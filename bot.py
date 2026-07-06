print("=== ПРОГРАММА ЗАПУСТИЛАСЬ! ===")
import vizdoom as vzd
import numpy as np
import cv2
import time
from enum import Enum

class ControlMode(Enum):
    MANUAL = "manual"  # Ручное управление через консоль
    AI = "ai"          # ИИ (пока заглушка)
    DEMO = "demo"      # Демонстрация (бот сам ходит)

class DoomBot:
    def __init__(self, mode=ControlMode.MANUAL):
        self.mode = mode
        self.game = None
        self.setup_game()
        
    def setup_game(self):
        print("Настраиваем игру...")
        self.game = vzd.DoomGame()
        
        self.game.set_doom_scenario_path(vzd.scenarios_path + "/basic.wad")
        self.game.set_doom_map("map01")
        self.game.set_screen_resolution(vzd.ScreenResolution.RES_640X480)
        self.game.set_render_hud(True)
        self.game.set_render_crosshair(True)
        self.game.set_render_decals(True)
        self.game.set_render_particles(True)
        self.game.set_window_visible(True)
        
        self.game.set_depth_buffer_enabled(True)
        self.game.set_labels_buffer_enabled(True)
        self.game.set_automap_buffer_enabled(True)
        
        self.game.add_available_button(vzd.Button.MOVE_FORWARD)
        self.game.add_available_button(vzd.Button.MOVE_BACKWARD)
        self.game.add_available_button(vzd.Button.TURN_LEFT)
        self.game.add_available_button(vzd.Button.TURN_RIGHT)
        self.game.add_available_button(vzd.Button.ATTACK)
        
        self.game.add_available_game_variable(vzd.GameVariable.HEALTH)
        self.game.add_available_game_variable(vzd.GameVariable.AMMO2)
        self.game.add_available_game_variable(vzd.GameVariable.KILLCOUNT)
        
        self.game.set_episode_timeout(10500)
        self.game.set_episode_start_time(10)
        self.game.set_living_reward(-1)
        
        print("Инициализация движка (может занять минуту)...")
        self.game.init()
        print("Движок запущен!")
        
        self.actions = [
            [1, 0, 0, 0, 0],  # 0: Вперед
            [0, 1, 0, 0, 0],  # 1: Назад
            [0, 0, 1, 0, 0],  # 2: Влево
            [0, 0, 0, 1, 0],  # 3: Вправо
            [0, 0, 0, 0, 1],  # 4: Стрелять
            [1, 0, 0, 0, 1],  # 5: Вперед + Стрелять
            [0, 0, 0, 0, 0],  # 6: Ничего
        ]
        
        print(f"Бот инициализирован в режиме: {self.mode.value}")
    
    def get_state(self):
        state = self.game.get_state()
        if state is None:
            return None
            
        screen = state.screen_buffer
        depth = state.depth_buffer if state.depth_buffer is not None else None
        labels = state.labels if state.labels is not None else []
        
        state_vector = np.array([
            self.game.get_game_variable(vzd.GameVariable.HEALTH),
            self.game.get_game_variable(vzd.GameVariable.AMMO2),
            self.game.get_game_variable(vzd.GameVariable.KILLCOUNT),
        ])
        
        return {
            'screen': screen,
            'depth': depth,
            'labels': labels,
            'state_vector': state_vector,
            'available_actions': list(range(len(self.actions)))
        }
    
    def manual_control(self):
        """Ручное управление через консоль"""
        print("\nКоманды: w(вперед), s(назад), a(влево), d(вправо), f(стрелять), q(выход)")
        cmd = input("Ваша команда: ").strip().lower()
        
        if cmd == 'q':
            return None  # Выход
        elif cmd == 'w':
            return self.actions[0]  # Вперед
        elif cmd == 's':
            return self.actions[1]  # Назад
        elif cmd == 'a':
            return self.actions[2]  # Влево
        elif cmd == 'd':
            return self.actions[3]  # Вправо
        elif cmd == 'f':
            return self.actions[4]  # Стрелять
        else:
            print("Неизвестная команда, бот стоит на месте")
            return self.actions[6]  # Ничего
    
    def demo_control(self, state):
        """Демонстрационный режим - бот сам ходит"""
        frame = self.game.get_episode_time()
        if frame % 35 == 0:
            return self.actions[4]  # Стрелять
        elif frame % 70 < 35:
            return self.actions[2]  # Влево
        else:
            return self.actions[0]  # Вперед
    
    def visualize(self, state):
        """Визуализация того, что видит бот"""
        if state is None:
            return
            
        screen = state['screen']
        cv2.imshow('Bot Vision - Screen', cv2.cvtColor(screen, cv2.COLOR_RGB2BGR))
        
        if state['depth'] is not None:
            depth_normalized = cv2.normalize(state['depth'], None, 0, 255, cv2.NORM_MINMAX)
            depth_colored = cv2.applyColorMap(depth_normalized.astype(np.uint8), cv2.COLORMAP_JET)
            cv2.imshow('Bot Vision - Depth', depth_colored)
        
        cv2.waitKey(1)
    
    def run(self, episodes=3):
        for episode in range(episodes):
            print(f"\n=== Эпизод {episode + 1}/{episodes} ===")
            self.game.new_episode()
            
            while not self.game.is_episode_finished():
                state = self.get_state()
                if state is None:
                    break
                
                self.visualize(state)
                
                # Выбор действия в зависимости от режима
                if self.mode == ControlMode.MANUAL:
                    action = self.manual_control()
                    if action is None:  # Пользователь нажал 'q'
                        print("Выход из игры...")
                        self.game.close()
                        cv2.destroyAllWindows()
                        return
                else:  # DEMO
                    action = self.demo_control(state)
                
                reward = self.game.make_action(action)
                
                # Показываем статистику
                health = self.game.get_game_variable(vzd.GameVariable.HEALTH)
                ammo = self.game.get_game_variable(vzd.GameVariable.AMMO2)
                kills = self.game.get_game_variable(vzd.GameVariable.KILLCOUNT)
                print(f"HP: {health} | Ammo: {ammo} | Kills: {kills}")
                
                time.sleep(0.05)
            
            print(f"Эпизод завершен. Награда: {self.game.get_total_reward()}")
        
        self.game.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    # Режим MANUAL - ручное управление через консоль
    bot = DoomBot(mode=ControlMode.MANUAL)
    bot.run(episodes=3)