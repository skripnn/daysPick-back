from pyngrok import ngrok
import subprocess
import clipboard

from telebot import TeleBot


def check_django_server():
    import socket
    a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    location = ("0.0.0.0", 8000)
    result_of_check = a_socket.connect_ex(location)

    if result_of_check != 0:
        print("Django is not started")

    a_socket.close()

    return result_of_check == 0


def start_nginx():
    print('Starting `nginx`...')
    subprocess.call('sudo -S brew services restart nginx', shell=True)


def stop_nginx():
    subprocess.call('sudo -S brew services stop nginx', shell=True)


def stop_ngrok():
    print("Stopping `ngrok`...")
    ngrok.kill()
    print('==> Successfully started `ngrok`')


def start_ngrok():
    print('Starting `ngrok`...')
    ngrok.connect()
    print(f'==> Successfully started `ngrok`')


def ngrok_process():
    ngrok_process = ngrok.get_ngrok_process()
    print('Stop the process when you finish')
    try:
        ngrok_process.proc.wait()
    except:
        stop_ngrok()
        stop_nginx()


def get_ngrok_address():
    tunnels = ngrok.get_tunnels()
    for tunnel in tunnels:
        if tunnel.proto == 'https':
            print(f'Ngrok address: {tunnel.public_url} was copied to clipboard\n')
            clipboard.copy(tunnel.public_url)
            return tunnel.public_url
    return None


def set_bot_webhook(address):
    if address:
        from timespick.keys import TELEGRAM_TOKEN_dev
        webhook_address = f"{address}/bot/{TELEGRAM_TOKEN_dev}"
        bot = TeleBot(TELEGRAM_TOKEN_dev)
        bot.set_webhook(url=webhook_address)
        print(f'==> Successfully set Telegram bot webhook to {address}')
        print(f'CHANGE TELEGRAM BOT DOMAIN here: https://t.me/BotFather')


def facebook_url_setup(address):
    if address:
        from timespick.keys import facebook_dev_id
        print(f'CHANGE FACEBOOK DEVELOPER DOMAIN here: https://developers.facebook.com/apps/{facebook_dev_id}/settings/basic/\n')


def start():
    start_nginx()
    start_ngrok()
    address = get_ngrok_address()
    set_bot_webhook(address)
    facebook_url_setup(address)
    ngrok_process()


if __name__ == '__main__':
    if check_django_server():
        start()
    else:
        print("Start the Django server")
