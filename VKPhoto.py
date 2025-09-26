import requests
import json
from tqdm import tqdm



class VKPhoto:

    def __init__(self, vk_token, vk_user_id, yandex_token, photo_count=5):
        self.vk_token = vk_token
        self.vk_user_id = vk_user_id
        self.yandex_token = yandex_token
        self.photo_count = photo_count
        self.photos_info = []

    def get_vk_photos(self):
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': self.vk_user_id,
            'album_id': 'profile',
            'extended': 1,
            'photo_sizes': 1,
            'count': 1000,
            'access_token': self.vk_token,
            'v': '5.131'
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                print(f"Error VK API: {data['error']['error_msg']}")
                return None

            return data['response']['items']
        except requests.exceptions.RequestException as e:
            print(f"Error VK API: {e}")
            return None

    def get_max_size_photo(self, photo):
        sizes = photo['sizes']
        max_size = max(sizes, key=lambda x: x['height'] * x['width'])
        return {
            'url': max_size['url'],
            'type': max_size['type'],
            'likes': photo['likes']['count'],
            'date': photo['date']
        }

    def process_photos(self):
        photos = self.get_vk_photos()
        if not photos:
            return False

        photos_sorted = sorted(
            photos,
            key=lambda x: max(s['height'] * s['width'] for s in x['sizes']),
            reverse=True
        )

        top_photos = photos_sorted[:self.photo_count]

        self.photos_info = [self.get_max_size_photo(photo) for photo in top_photos]

        likes_count = {}
        for photo in self.photos_info:
            likes = photo['likes']
            if likes in likes_count:
                likes_count[likes] += 1
                photo['file_name'] = f"{likes}_{photo['date']}.jpg"
            else:
                likes_count[likes] = 1
                photo['file_name'] = f"{likes}.jpg"

        return True

    def create_yandex_folder(self, folder_name):
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {
            'Authorization': f'OAuth {self.yandex_token}'
        }
        params = {
            'path': folder_name
        }

        try:
            response = requests.put(url, headers=headers, params=params)
            if response.status_code not in [201, 409]:
                response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            return False

    def upload_to_yandex(self, folder_name):
        if not self.create_yandex_folder(folder_name):
            return False

        url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
        headers = {
            'Authorization': f'OAuth {self.yandex_token}'
        }

        for photo in tqdm(self.photos_info, desc="loader_photos"):
            params = {
                'url': photo['url'],
                'path': f"{folder_name}/{photo['file_name']}"
            }

            try:
                response = requests.post(url, headers=headers, params=params)
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                print(f"Error {photo['file_name']}: {e}")
                continue

        return True

    def save_photos_info_to_json(self, filename='photos_info.json'):
        data_to_save = []
        for photo in self.photos_info:
            data_to_save.append({
                'file_name': photo['file_name'],
                'size': photo['type']
            })

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            print(f"info save file {filename}")
            return True
        except IOError as e:
            print(f"Error: {e}")
            return False

def main():
    vk_token = "ваш сервисный токен"
    vk_user_id =  "числовой id пользователя"
    yandex_token = "токен с полигона яндекса"

    downloader = VKPhoto(
        vk_token=vk_token,
        vk_user_id=vk_user_id,
        yandex_token=yandex_token
    )

    if not downloader.process_photos():
        print("Ошибка загрузки фото из VK")
        return

    folder_name = 'VK_Photos' # можно изменить на любое другое имя

    if not downloader.upload_to_yandex(folder_name):
        print("Ошибка загрузки на Яндекс.Диск")
        return

    if not downloader.save_photos_info_to_json():
        print("Ошибка сохранения информации о фото")
    else:
        print("Все операции завершены успешно!")

if __name__ == '__main__':
    main()