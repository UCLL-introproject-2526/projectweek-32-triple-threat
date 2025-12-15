import pygame


def create_main_surface():
    screen_size = (1024, 768)
    pygame.display.set_mode(screen_size)


def main():
    pygame.init()
    create_main_surface()

    while True:
        pass

main()
