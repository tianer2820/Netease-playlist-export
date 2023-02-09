import requests
import time
import qrcode
import pickle
import os
import json


def check_login(s: requests.Session, api_url: str) -> bool:
    """get the login status"""
    ret = s.get(api_url + '/login/status', params={'time': time.time()})
    if ret.status_code != 200:
        return False
    status_json = ret.json()
    account_type = status_json['data']['account']['type']
    return account_type > 0


def qr_login(s: requests.Session, api_url: str):
    """generate a qr code, wait until the user logged in"""
    qr_key = s.get(api_url + "/login/qr/key", params={"time": time.time()})
    qr_key = qr_key.json()['data']['unikey']
    qr_code = s.get(api_url + '/login/qr/create',
                        params={"time": time.time(), "key": qr_key})
    qr_url = qr_code.json()['data']['qrurl']
    print(qr_url)

    qr_img = qrcode.make(qr_url)
    qr_img = qr_img.get_image()
    qr_img.show()
    print("Please scan the qrcode with the Netease App and allow login")

    # check qr code status
    while True:
        time.sleep(1)
        qr_status = s.get(api_url + '/login/qr/check',
                                params={"time": time.time(), "key": qr_key})
        qr_status_json = qr_status.json()
        code = qr_status_json['code']
        if code == 801:
            print('waiting for scan')
        elif code == 802:
            print('code scanned by user {}, waiting for confirm'.format(qr_status_json['nickname']))
        elif code == 803:
            print('login succeed')
            login_cookie = qr_status_json['cookie']
            print(qr_status.cookies)
            break
        else:
            # something wrong, maybe qr code outdated
            print('something went wrong, exiting')
            exit(1)

    # wait until the server login status is updated
    while not check_login(s):
        time.sleep(0.5)
    

def get_user_id(s: requests.Session, api_url: str) -> int:
    account_resp = s.get(api_url + '/user/account')
    account_json = account_resp.json()
    account_id = account_json['account']['id']
    return account_id


def get_playlists(s: requests.Session, api_url: str, user_id: int):
    play_lists = []
    offset = 0
    while True:
        playlist_resp = s.get(api_url + '/user/playlist',
                            params={'uid': user_id, 'offset': offset})
        playlist_json = playlist_resp.json()

        current_lists = playlist_json['playlist']
        for l in current_lists:
            play_lists.append({
                'name': l['name'],
                'id': l['id'],
            })
        offset += len(current_lists)
        if playlist_json['more'] == False:
            break
    return play_lists


def get_playlist_details(s: requests.Session, api_url: str, list_id: int):
    playlist_detail_resp = s.get(api_url + '/playlist/detail', params={'id': list_id})
    playlist_detail_json = playlist_detail_resp.json()
    return playlist_detail_json['playlist']


def export_playlists(
        api_url: str = 'http://localhost:3000',
        output_dir: str = './exported_playlists',
        ignore_copied: bool = True,
        cookie_file: str = None) -> bool:
    """return true if operation finished without error"""

    s = requests.Session()

    # check output directory
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    elif os.path.isfile(output_dir):
        print('output dir is a file!')
        return False

    # try load past cookies
    if cookie_file is not None:
        if os.path.isfile(cookie_file):
            with open(cookie_file, 'rb') as f:
                cookies = pickle.load(f)
                if cookies is not None:
                    s.cookies = cookies

    # check login
    if check_login(s, api_url) == 1:
        print('Already logged in')
    else:
        print('Need to login now')
        qr_login(s, api_url)
        # save cookies for later use
        if cookie_file is not None:
            with open(cookie_file, 'wb') as f:
                pickle.dump(s.cookies, f)

    # get user id
    user_id = get_user_id(s, api_url)
    print("User id:", user_id)

    # get all playlists names and id
    play_lists = get_playlists(s, api_url, user_id)
    print(f'{len(play_lists)} play lists found')

    # get playlist details
    for i, l in enumerate(play_lists):
        name = l['name']
        list_id = l['id']
        print(f"[{i}/{len(play_lists)}] Getting playlist {name}...")
        list_detail = get_playlist_details(s, api_url, list_id)

        # skip copied playlist
        if list_detail['userId'] != user_id and ignore_copied:
            print(f'skipping copied playlist {name}')
            continue

        # export tracks in the list
        tracks = list_detail['tracks']
        simplified_list = []
        for t in tracks:
            track_name = t['name']
            artist_name = t['ar'][0]['name']
            album_name = t['al']['name']
            cd_name = t['cd']

            simplified_list.append(
                {
                'track': track_name,
                'artist': artist_name,
                'album': album_name,
                'cd': cd_name,
                }
            )
        
        with open(os.path.join(output_dir, f'{name}.json'), 'wt', encoding='utf8') as f:
            json.dump(simplified_list, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':

    export_playlists(
        api_url='http://localhost:3000',
        output_dir='./exported_playlists',
        ignore_copied=True,  # ignore playlists that are not created by you
        cookie_file='./cookie.pkl'  # does not have to exist, you will be asked to login with qr code if this file does not exist
    )
