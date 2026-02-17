import threading
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
import pygame
from io import BytesIO
from PIL import Image
import time

secrets = {}
with open("id.txt", "r") as file:
    for line in file:
        key, value = line.strip().split("=")
        secrets[key] = value

CLIENT_ID = secrets["CLIENT_ID"]
CLIENT_SECRET = secrets["CLIENT_SECRET"]
REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPE = "user-read-playback-state user-read-currently-playing"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SCOPE
))

shared_song_info = {
    "playing": None,
    "album_cover": None,
    "rotated_angles_cache": [],
    "rotated_covers_cache": [],
    "last_album_cover_url": None
}

lock = threading.Lock()
running = True

def spotify_api_grabber(sp):
    global running
    while running:
        current = sp.current_playback()
        if current and current['item']:
            if current['device']['name'] == "Salon":
                album_cover_url = current['item']['album']['images'][0]['url']
                with lock:
                    shared_song_info["playing"] = current['is_playing']
                    if shared_song_info["last_album_cover_url"] != album_cover_url:
                        response = requests.get(album_cover_url)
                        img = Image.open(BytesIO(response.content))
                        img = img.convert("RGB")
                        img_ratio = img.width / img.height
                        screen_ratio = screen_width / screen_height
                        if img_ratio > screen_ratio:
                            new_width = screen_width
                            new_height = int(screen_width / img_ratio)
                        else:
                            new_height = screen_height
                            new_width = int(screen_height * img_ratio)
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                        mode = img.mode
                        size = img.size
                        data = img.tobytes()
                        album_cover = pygame.image.fromstring(data, size, mode)
                        shared_song_info["album_cover"] = album_cover
                        shared_song_info["last_album_cover_url"] = album_cover_url
                        shared_song_info["rotated_angles_cache"] = []
                        shared_song_info["rotated_covers_cache"] = []
        else:
            with lock:
                shared_song_info["playing"] = None
                shared_song_info["album_cover"] = None
        time.sleep(0.1)

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()
screen_width, screen_height = screen.get_size()

def display_album_cover(album_cover, angle):
    angle = angle % 360
    with lock:
        rotated_angles_cache = shared_song_info["rotated_angles_cache"]
        rotated_covers_cache = shared_song_info["rotated_covers_cache"]
    if angle not in rotated_angles_cache:
        rotated_covers_cache.append(pygame.transform.rotate(album_cover, angle))
        rotated_angles_cache.append(angle)
    rotated_surface = rotated_covers_cache[rotated_angles_cache.index(angle)]
    rect = rotated_surface.get_rect(center=(screen_width // 2, screen_height // 2))
    screen.blit(rotated_surface, rect)

thread = threading.Thread(target=spotify_api_grabber, args=(sp,))
thread.start()

angle = 0

mask = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
mask.fill((0, 0, 0, 255))
pygame.draw.circle(
    mask,
    (0, 0, 0, 0),  # Fully transparent
    (screen_width // 2, screen_height // 2),
    screen_height // 2
)

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    with lock:
        playing = shared_song_info["playing"]
        album_cover = shared_song_info["album_cover"]
    if playing == True:
        angle -= 2
        display_album_cover(album_cover, angle)
    elif playing == False:
        display_album_cover(album_cover, angle)
    else:
        screen.fill((0, 0, 0))
        angle = 0
    screen.blit(mask, (0, 0))
    pygame.draw.circle(
        screen,
        (0, 0, 0),
        (screen_width // 2, screen_height // 2),
        20,
    )
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
thread.join()