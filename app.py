import pygame
import sys
import os 
import random # Is nu niet nodig, maar handig voor later

# --- GLOBALE CONFIGURATIE ---
W, H = 1024, 768
ZWART = (0, 0, 0)
ROOD = (255, 0, 0)
WIT = (255, 255, 255)
CLOCK = pygame.time.Clock()

# Globale lijst voor de frames van de speler
PLAYER_IMAGES = [] 
# ---------------------------


def create_main_surface():
    """Initialiseert het Pygame venster en retourneert het schermobject."""
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Triple Threat Runner: Animated Player")
    return screen

def load_assets():
    """Laadt alle afbeeldingen voor de speler animatie."""
    global PLAYER_IMAGES
    
    # --- LAAD AFBEELDINGEN ---
    try:
        print("Bezig met laden van speler afbeeldingen...")
        # We laden alle 8 frames van de raceauto
        for i in range(8):
            # *** DEZE REGEL IS AANGEPAST ***
            # Het pad is nu 'images/SportsRacingCar_X.png'
            path = os.path.join('images', f'SportsRacingCar_{i}.png') 
            # *******************************
            
            img = pygame.image.load(path).convert_alpha()
            PLAYER_IMAGES.append(img)
        print(f"Succesvol {len(PLAYER_IMAGES)} frames geladen.")
            
    except pygame.error as e:
        # De fallback (rode cirkel) wordt gebruikt als het laden mislukt.
        print(f"FATALE FOUT: Afbeeldingen konden niet geladen worden. Controleer of de 'images' map direct in de projectmap staat.")
        print(f"Fout details: {e}")
        PLAYER_IMAGES = [] # Zorgt ervoor dat de fallback gebruikt wordt


def main():
    pygame.init()
    screen = create_main_surface()
    load_assets() # Laadt de 8 frames in de globale lijst
    
    running = True 
    animation_frame_counter = 0.0 # Bepaalt welk frame we tekenen
    animation_speed = 0.25      # Hoe snel de frames wisselen (hoger = sneller)
    
    # De Game Loop
    while running:
        # Zorgt voor een constante snelheid
        CLOCK.tick(60) 

        # 1. EVENT HANDLING (Zorgt ervoor dat je het venster kunt sluiten)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # 2. GAME LOGICA UPDATE
        # Update de animatie teller
        animation_frame_counter += animation_speed
        
        # Reset de teller als we het einde van de frames hebben bereikt
        if animation_frame_counter >= len(PLAYER_IMAGES) and PLAYER_IMAGES:
             animation_frame_counter = 0.0

        # 3. TEKENEN / RENDERING
        screen.fill(ZWART) 

        # *** Teken de geanimeerde speler ***
        if PLAYER_IMAGES:
            # Bepaal het huidige frame (zorg dat het een integer is binnen de bounds)
            frame_index = int(animation_frame_counter) % len(PLAYER_IMAGES)
            current_img = PLAYER_IMAGES[frame_index]
            
            # Bepaal de positie (midden van het scherm, iets boven de onderkant)
            rect = current_img.get_rect(center=(W // 2, H - 150))
            
            # Teken de afbeelding
            screen.blit(current_img, rect)
        else:
             # Fallback: Teken een grote rode cirkel als de afbeeldingen falen
             pygame.draw.circle(screen, ROOD, (W // 2, H - 150), 50)
        # ***********************************
        
        # 4. UPDATE HET SCHERM
        pygame.display.flip()

    # SLUIT PYGAME NETJES AF
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()