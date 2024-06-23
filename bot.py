import asyncio
import logging
from os import remove

from ultralytics import YOLO

from aiogram import Bot, Dispatcher, types, F
from aiogram.types import FSInputFile
from aiogram.filters.command import Command

#TYPES
objects = {
    'NATION DEM':'Демография',
    'NATION DOR':'Безопасные качественные дороги',
    'NATION ECO':'Экология',
    'NATION JIL':'Жилье и городская среда',
    'NATION KUL':'Культура',
    'NATION OBR':'Образование',
    'NATION ZDR':'Здравоохранение',
    'NATION TUR':'Туризм'
}

# ДЛЯ РАБОТЫ БОТА НУЖНО В C:/tmp создать папки photo и models, в models поместить модели correct.pt и type.pt

model_correct_path = r'C:/tmp/models/correct.pt' # путь к модели корректности
model_type_path = r'C:/tmp/models/type.pt' # путь к модели определения нац. проекта
model_yolo_path = r'C:/tmp/models/yolov8m.pt' # путь к дефолтной моделе yolov8
model_fonts_path = r'C:/tmp/models/fonts.pt'

model_correct = YOLO(model_correct_path) 
model_type = YOLO(model_type_path)
model_yolo = YOLO(model_yolo_path)
model_fonts = YOLO(model_fonts_path)

def predict_correct(path, name): # функция для проверки корректности
    resultPath = f'C:/tmp/photo/correct-{name}.jpg'
    results = model_correct.predict(path, agnostic_nms=True)[0]
    results.save(filename=resultPath)
    if len(results.boxes) > 0:
        output = []
        for boxes in results.boxes:
            output.append(results.names[int(boxes.cls[0].item())])
    else:
        output = ['None']
    
    text = ', '.join(output)
    return [resultPath, text, output]

def predict_type(path, name): # функция для определения нац. проекта
    resultPath = f'C:/tmp/photo/type-{name}.jpg'
    results = model_type.predict(path, agnostic_nms=True)[0]
    results.save(filename=resultPath)
    if len(results.boxes) > 0:
        output = []
        for boxes in results.boxes:
            output.append(results.names[int(boxes.cls[0].item())])
    else:
        output = ['None']
    
    text = ', '.join(output)
    return [resultPath, text, output] # возвращает список с путем к файлу и текстомвым оутпутом + список найденных обьектов

def predict_people(path, name): # функция для определения людей на фото
    resultPath = f'C:/tmp/photo/people-{name}.jpg'
    results = model_yolo.predict(path, classes=[0])[0]
    results.save(filename=resultPath)
    if len(results.boxes) > 0:
        return [resultPath, True]
    else:
        return [resultPath, False] # возвращает список с путем к файлу и булевый тип данных: False - нет людей, True - есть люди на фото.
    
def predict_fonts(path, name): # функция для определения корректности шрифта
    resultPath = f'C:/tmp/photo/fonts-{name}.jpg'
    results = model_fonts.predict(path, agnostic_nms=True)[0]
    results.save(filename=resultPath)
    if len(results.boxes) > 0:
        output = []
        for boxes in results.boxes:
            output.append(results.names[int(boxes.cls[0].item())])
    else:
        output = ['None']
    
    return [resultPath, output]


# t.me/NationProjectCorrectBot - бот
TOKEN = '7022310583:AAHdo8bcx6ZgoqUZs0wwP_lHRKMQf5PKW_E'
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("ℹ️ Добро пожаловать!\nЭтот бот предназначен для определения брендирования национального проекта!\n\nДля начала взаимодействования с ботом отправьте фотографию!")

@dp.message(F.photo)
async def sendGet(message: types.Message):
    file = message.photo[-1]
    file_name = file.file_id
    file_path = f'C:/tmp/photo/{file_name}.jpg'
    try:
        await bot.download(file=file, destination=file_path) # скачивание изображения
        preprocessing = await message.answer("⌛️ Подождите, изображение обрабатывается..")

        try:
            objectType = predict_type(file_path, file_name)
            photoType = FSInputFile(objectType[0])
            
            if ['None'] != objectType[2]:
                await preprocessing.edit_text("✅ Определён тип национального проекта")
                correctTrust = predict_correct(file_path, file_name)
                photoCorrect = FSInputFile(correctTrust[0]) # корректность национального обьекта

                if 'not-correct' not in correctTrust[1]:
                    await preprocessing.edit_text("✅ Брендирование национального проекта определено как корректное")
                    peopleTrust = predict_people(file_path, file_name)
                    photoPeople = FSInputFile(peopleTrust[0])

                    if not peopleTrust[1]:
                        await preprocessing.edit_text("✅ На фотографии не обнаружено людей")
                        fontsTrust = predict_fonts(file_path, file_name)

                        if 'Bad_font' in fontsTrust[1] or ['None'] == fontsTrust[1]:
                            await message.answer_photo(photoType, f"⭐️ Определен тип национального проекта:\n\n<b>{', '.join(objects.get(i, i) for i in objectType[2])}</b>\n\n⚠️ <i>Возможно в брендировании используется некорректный шрифт</i>", parse_mode='HTML') 
                        else:
                            await message.answer_photo(photoType, f"⭐️ Определен тип национального проекта:\n\n<b>{', '.join(objects.get(i, i) for i in objectType[2])}</b>", parse_mode='HTML') 

                        remove(fontsTrust[0])
                    else:
                        await message.answer_photo(photoPeople, f"❗️ Обнаружено некорректное брендирование национального проекта (на фотографии не должно присутствовать людей)")
                    
                    remove(peopleTrust[0])
                else:
                    await message.answer_photo(photoCorrect, f"❗️ Обнаружено некорректное брендирование национального проекта")
                
                remove(correctTrust[0])
            else:
                await message.answer_photo(photoType, f"❗️ Не удалось обнаружить брендирование национальных проектов на фотографии")

            await preprocessing.delete()
            remove(file_path)
            remove(objectType[0])
        except:
            await message.answer("❗️ Не удалось обработать изображение")
            await preprocessing.delete()
    except:
        await message.answer("❗️ Изображение не получено") 

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
