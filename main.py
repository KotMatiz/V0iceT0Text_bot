import requests
import whisper
import subprocess
import torch
import os
import telebot
from telebot import types
from concurrent.futures import ThreadPoolExecutor

bot = telebot.TeleBot('6867622191:AAEr1xMeD5MdQMQi2cEw-2piNCmcZN7tT-U')

executor = ThreadPoolExecutor(max_workers=4)  # Количество потоков для параллельной обработки


def save_audio_from_response(response, path='audio.mp3'):
    if response.status_code == 200:
        with open(path, 'wb') as file:
            file.write(response.content)


def transcribe_audio(path, model_size='medium'):
    device = torch.device("cpu")
    model = whisper.load_model(model_size)
    result = model.transcribe(path)
    return result["text"]


def process_audio(file_info, chat_id, processing_message_id):
    file_path = file_info.file_path
    url = f'https://api.telegram.org/file/bot{bot.token}/{file_path}'
    response = requests.get(url)
    audio_mp3_path = f'audio_{processing_message_id}.mp3'
    audio_wav_path = f'audio_{processing_message_id}.wav'

    save_audio_from_response(response, audio_mp3_path)

    if audio_mp3_path[-3:] != 'wav':
        subprocess.call(['ffmpeg', '-i', audio_mp3_path, audio_wav_path, '-y', '-loglevel', 'error'])

    transcript = transcribe_audio(audio_wav_path)
    cleanup_files(audio_wav_path, audio_mp3_path)

    bot.edit_message_text(chat_id=chat_id, message_id=processing_message_id, text=transcript)


def cleanup_files(*file_paths):
    for path in file_paths:
        if os.path.exists(path):
            os.remove(path)


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("👋 Поздороваться")
    btn2 = types.KeyboardButton("❓ О боте")
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id,
                     '🎙️ Привет!\nЯ бот для перевода Голосовых сообщений в Текст на основе ИИ.\n\nКак использовать: перешлите мне голосовое сообщение – а я отправлю вам распознанный текст!',
                     reply_markup=markup)


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    # Отправка сообщения о начале обработки с ответом на голосовое сообщение
    processing_message = bot.reply_to(message, "Идет обработка, пожалуйста, ожидайте...")
    processing_message_id = processing_message.message_id
    file_info = bot.get_file(message.voice.file_id)

    # Параллельная обработка аудио
    executor.submit(process_audio, file_info, message.chat.id, processing_message_id)


@bot.message_handler(content_types=['text'])
def func(message):
    if message.text == "👋 Поздороваться":
        bot.send_message(message.chat.id, text=f"Привет, {message.from_user.first_name}, надеюсь я смогу тебе помочь)")
    elif message.text == "❓ О боте":
        bot.send_message(message.chat.id, text="Я могу расшифровать твои голосовые сообщения в текст.")
    else:
        bot.send_message(message.chat.id, "Прости, я понимаю только голосовые сообщения.")


if __name__ == '__main__':
    bot.polling(none_stop=True, interval=0)
