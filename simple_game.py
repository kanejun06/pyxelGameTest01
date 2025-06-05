import pyxel
import math
import random
import time

TOUCH_CONTROL = False  # タッチ操作の有効化フラグ

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1.5, 4.0)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.life = 30
        self.size = 1

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.life -= 1
        return self.life > 0

    def draw(self):
        pyxel.pset(self.x, self.y, self.color)

class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 2
        angle = random.uniform(-60, 60)
        speed = 2
        self.dx = speed * math.sin(math.radians(angle))
        self.dy = -speed * math.cos(math.radians(angle))
        self.trail_positions = []
        self.max_trail = 8

    def update(self, app):
        self.trail_positions.insert(0, (self.x, self.y))
        if len(self.trail_positions) > self.max_trail:
            self.trail_positions.pop()

        next_x = self.x + self.dx
        next_y = self.y + self.dy
        
        if next_x < 0:
            self.x = 0
            self.dx = abs(self.dx)
        elif next_x > pyxel.width - self.size:
            self.x = pyxel.width - self.size
            self.dx = -abs(self.dx)
        else:
            self.x = next_x
            
        if next_y < 0:
            self.y = 0
            self.dy = abs(self.dy)
        else:
            self.y = next_y

        if (self.y + self.size > app.paddle_y and 
            self.x + self.size > app.paddle_x and 
            self.x < app.paddle_x + app.paddle_width):
            
            relative_intersect_x = (app.paddle_x + (app.paddle_width / 2)) - self.x
            normalized_intersect = relative_intersect_x / (app.paddle_width / 2)
            bounce_angle = normalized_intersect * 60
            
            speed = math.sqrt(self.dx ** 2 + self.dy ** 2)
            self.dx = -speed * math.sin(math.radians(bounce_angle))
            self.dy = -speed * math.cos(math.radians(bounce_angle))
            
            self.y = app.paddle_y - self.size

    def draw(self):
        for i, (trail_x, trail_y) in enumerate(self.trail_positions[1:], 1):
            alpha = (self.max_trail - i) / self.max_trail
            color = 1 if i > self.max_trail // 2 else 5
            pyxel.rect(trail_x, trail_y, self.size, self.size, color)
        
        pyxel.rect(self.x, self.y, self.size, self.size, 7)

class Item:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 4
        self.speed = 1
        self.active = True

    def update(self):
        self.y += self.speed
        return self.y < pyxel.height

    def draw(self):
        if pyxel.frame_count % 30 < 15:
            color = 11
        else:
            color = 10
        pyxel.rect(self.x, self.y, self.size, self.size, color)

class ExplosionEffect:
    def __init__(self, x, y, combo):
        self.x = x
        self.y = y
        self.combo = combo
        self.life = 8
        self.max_life = 8
        base_radius = 12
        combo_bonus = combo * 6
        self.max_radius = min(base_radius + combo_bonus, 60)
        
    def update(self):
        self.life -= 1
        return self.life > 0
    
    def get_current_radius(self):
        progress = self.life / self.max_life
        if progress > 0.4:
            t = (1 - progress) / 0.6
            return self.max_radius * (1 - (1 - t) * (1 - t) * (1 - t) * (1 - t))
        else:
            t = progress / 0.4
            return self.max_radius * (t * t * t * t)
    
    def draw(self):
        radius = self.get_current_radius()
        num_trails = min(self.combo * 4 + 8, 32)
        
        for i in range(num_trails):
            angle = (i / num_trails) * math.pi * 2
            trail_x = self.x + math.cos(angle) * radius
            trail_y = self.y + math.sin(angle) * radius
            color = 10 if self.combo >= 3 else 6
            pyxel.pset(trail_x, trail_y, color)

        center_color = 7 if self.combo < 3 else 10
        center_size = min(1 + self.combo // 2, 4)
        pyxel.circ(self.x, self.y, center_size, center_color)

class App:
    def __init__(self):
        pyxel.init(160, 120, title="Break the blocks")
        self.touch_x = 0
        self.is_touching = False
        self.init_game()
        pyxel.run(self.update, self.draw)
    
    def init_game(self):
        self.paddle_x = 80
        self.paddle_width = 24
        self.paddle_height = 2
        self.paddle_y = 110
        self.paddle_trail = []
        self.max_paddle_trail = 4
        self.paddle_opacity = 1.0
        self.paddle_exit_started = False
        self.paddle_exit_speed = 0
        
        self.balls = [Ball(80, 90)]
        
        self.blocks = []
        self.block_width = 10
        self.block_height = 8
        for row in range(5):
            for col in range(14):
                self.blocks.append({
                    'x': col * (self.block_width + 1) + 5,
                    'y': row * (self.block_height + 2) + 10,
                    'active': True,
                    'fall_speed': 0,
                    'color': 8 + row % 7,
                    'rotation': 0,
                    'rotate_speed': 0,
                    'fall_delay': 0,
                    'horizontal_speed': 0
                })
        
        self.particles = []
        self.items = []
        self.game_cleared = False
        self.game_over = False
        self.game_over_timer = 0
        self.clear_message_y = 60
        self.start_time = time.time()
        self.clear_time = 0
        self.bonus_time = 0
        self.ball_bonus = 0
        self.combo_bonus = 0
        self.total_combo_bonus = 0  # 累積コンボボーナスを追加
        
        self.current_combo = 0
        self.max_combo = 0  # 最大コンボ数を記録
        self.combo_timer = 0
        self.max_combo_timer = 30
        self.screen_shake = {'x': 0, 'y': 0, 'duration': 0, 'magnitude': 0}
        self.combo_text = {'text': '', 'x': 0, 'y': 0, 'timer': 0}
        self.explosion_effects = []

    def update(self):
        if self.game_cleared:
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.init_game()
            return

        if self.game_over:
            self.update_game_over()
            if pyxel.btnp(pyxel.KEY_SPACE):
                self.init_game()
            return

        self.update_paddle()
        
        if self.combo_timer > 0:
            self.combo_timer -= 1
        elif self.current_combo > 0:
            self.current_combo = 0
        
        self.update_screen_shake()
        
        self.explosion_effects = [effect for effect in self.explosion_effects if effect.update()]
        
        active_balls = []
        for ball in self.balls:
            ball.update(self)
            if ball.y < pyxel.height:
                active_balls.append(ball)
        self.balls = active_balls
        
        if not self.balls:
            self.start_game_over()
            return
        
        self.check_collisions()
        self.particles = [p for p in self.particles if p.update()]
        
        active_items = []
        for item in self.items:
            if item.active and item.update():
                if (item.y + item.size > self.paddle_y and
                    item.x + item.size > self.paddle_x and
                    item.x < self.paddle_x + self.paddle_width):
                    item.active = False
                    self.add_new_ball()
                if item.active:
                    active_items.append(item)
        self.items = active_items
        
        if not any(block['active'] for block in self.blocks):
            if not self.game_cleared:
                self.clear_time = time.time() - self.start_time
                # 複数ボールのボーナス
                remaining_balls = len(self.balls)
                if remaining_balls > 1:
                    self.ball_bonus = remaining_balls - 1
                else:
                    self.ball_bonus = 0
                # 合計ボーナスを計算して適用
                self.combo_bonus = self.total_combo_bonus
                self.bonus_time = self.ball_bonus + self.combo_bonus
                self.clear_time = max(0, self.clear_time - self.bonus_time)
            self.game_cleared = True

    def draw(self):
        pyxel.cls(0)
        
        shake_x = self.screen_shake['x']
        shake_y = self.screen_shake['y']
        
        if self.game_cleared:
            if pyxel.frame_count % 30 < 20:
                pyxel.text(65 + shake_x, self.clear_message_y - 20 + shake_y, "FINISH!!!", 7)
            
            # オリジナルの時間を表示
            original_time = self.clear_time + self.bonus_time
            o_minutes = int(original_time // 60)
            o_seconds = int(original_time % 60)
            o_milliseconds = int((original_time * 100) % 100)
            original_text = f"ORIGINAL TIME: {o_minutes:02d}:{o_seconds:02d}.{o_milliseconds:02d}"
            pyxel.text(35 + shake_x, self.clear_message_y + shake_y, original_text, 13)
            
            if self.bonus_time > 0:
                if self.ball_bonus > 0:
                    ball_text = f"BALL BONUS! -{self.ball_bonus}s ({len(self.balls)} balls)"
                    pyxel.text(30 + shake_x, self.clear_message_y + 10 + shake_y, ball_text, 10)
                
                if self.combo_bonus > 0:
                    combo_text = f"COMBO BONUS! -{self.combo_bonus:.1f}s (Max {self.max_combo} combo)"
                    pyxel.text(30 + shake_x, self.clear_message_y + 20 + shake_y, combo_text, 11)
                
                # ボーナス適用後の最終時間を表示（赤色で点滅）
                final_time = self.clear_time
                f_minutes = int(final_time // 60)
                f_seconds = int(final_time % 60)
                f_milliseconds = int((final_time * 100) % 100)
                final_text = f"FINAL TIME: {f_minutes:02d}:{f_seconds:02d}.{f_milliseconds:02d}"
                if pyxel.frame_count % 30 < 20:  # FINISHと同じ点滅タイミング
                    pyxel.text(35 + shake_x, self.clear_message_y + 30 + shake_y, final_text, 8)  # 8は赤色
            
            if TOUCH_CONTROL:
                pyxel.text(40 + shake_x, self.clear_message_y + 45 + shake_y, "TOUCH TO RESTART", 6)
            else:
                pyxel.text(40 + shake_x, self.clear_message_y + 45 + shake_y, "PRESS SPACE TO RESTART", 6)
            return
        
        if self.game_over:
            for block in self.blocks:
                if block['active']:
                    if block['rotate_speed'] != 0:
                        self.draw_rotated_block(
                            block['x'] + shake_x,
                            block['y'] + shake_y,
                            self.block_width,
                            self.block_height,
                            block['color'],
                            block['rotation']
                        )
                    else:
                        pyxel.rect(
                            block['x'] + shake_x,
                            block['y'] + shake_y,
                            self.block_width,
                            self.block_height,
                            block['color']
                        )
            
            if self.paddle_opacity > 0:
                for i, trail_x in enumerate(self.paddle_trail):
                    alpha = (self.max_paddle_trail - i) / self.max_paddle_trail * self.paddle_opacity
                    if alpha > 0.3:
                        color = 1 if i > self.max_paddle_trail // 2 else 5
                        pyxel.rect(trail_x + shake_x, self.paddle_y + shake_y, 
                                self.paddle_width, self.paddle_height, color)
                
                if self.paddle_opacity > 0.7:
                    color = 7
                elif self.paddle_opacity > 0.4:
                    color = 6
                else:
                    color = 5
                pyxel.rect(self.paddle_x + shake_x, self.paddle_y + shake_y, 
                          self.paddle_width, self.paddle_height, color)
            
            if self.game_over_timer > 30 and (self.game_over_timer // 10) % 2 == 0:
                pyxel.text(70, 50, "OOPS!", 8)
                if self.paddle_opacity <= 0:
                    pyxel.text(40, 70, "PRESS SPACE TO RESTART", 7)
            return
        
        # パドルの残像を描画
        for i, trail_x in enumerate(self.paddle_trail):
            alpha = (self.max_paddle_trail - i) / self.max_paddle_trail
            if alpha > 0.7:
                color = 6
            elif alpha > 0.4:
                color = 5
            else:
                color = 1
            pyxel.rect(trail_x + shake_x, self.paddle_y + shake_y, 
                      self.paddle_width, self.paddle_height, color)
        
        # 現在のパドルを描画
        pyxel.rect(self.paddle_x + shake_x, self.paddle_y + shake_y, 
                  self.paddle_width, self.paddle_height, 7)
        
        for ball in self.balls:
            ball.draw()
        
        for block in self.blocks:
            if block['active']:
                pyxel.rect(block['x'] + shake_x, block['y'] + shake_y, 
                          self.block_width, self.block_height, block['color'])
        
        for effect in self.explosion_effects:
            effect.draw()
        
        for particle in self.particles:
            particle.draw()
        
        for item in self.items:
            item.draw()
        
        if self.combo_text['timer'] > 0:
            color = 10 if self.current_combo >= 3 else 7
            pyxel.text(
                self.combo_text['x'] + shake_x,
                self.combo_text['y'] + shake_y,
                self.combo_text['text'],
                color
            )
            self.combo_text['timer'] -= 1

    def update_screen_shake(self):
        if self.screen_shake['duration'] > 0:
            magnitude = self.screen_shake['magnitude']
            if magnitude < 1:
                shake = 1 if random.random() < magnitude else 0
            else:
                shake = random.randint(-int(magnitude), int(magnitude))
            self.screen_shake['x'] = shake
            self.screen_shake['y'] = shake
            self.screen_shake['duration'] -= 1
        else:
            self.screen_shake['x'] = 0
            self.screen_shake['y'] = 0
            self.screen_shake['magnitude'] = 0

    def add_screen_shake(self, combo):
        if combo >= 2:
            if combo == 2:
                magnitude = 0.5
                duration = 1
            elif combo == 3:
                magnitude = 1
                duration = 3
            elif combo == 4:
                magnitude = 2
                duration = 5
            else:
                magnitude = 3
                duration = 8
            
            self.screen_shake['magnitude'] = magnitude
            self.screen_shake['duration'] = duration

    def start_game_over(self):
        self.game_over = True
        self.game_over_timer = 0
        self.screen_shake['magnitude'] = 3
        self.screen_shake['duration'] = 8
        
        self.paddle_exit_started = True
        self.paddle_exit_speed = 1
        
        for block in self.blocks:
            if block['active']:
                block['fall_speed'] = random.uniform(2.0, 4.0)
                if random.random() < 0.3:
                    block['rotate_speed'] = random.uniform(-15, 15)
                block['fall_delay'] = random.randint(0, 20)
                if random.random() < 0.5:
                    block['horizontal_speed'] = random.uniform(-1.5, 1.5)

    def update_game_over(self):
        self.game_over_timer += 1
        
        if self.screen_shake['duration'] > 0:
            magnitude = self.screen_shake['magnitude']
            self.screen_shake['x'] = random.randint(-magnitude, magnitude)
            self.screen_shake['y'] = random.randint(-magnitude, magnitude)
            self.screen_shake['duration'] -= 1
        else:
            self.screen_shake['x'] = 0
            self.screen_shake['y'] = 0
            self.screen_shake['magnitude'] = 0
        
        for block in self.blocks:
            if block['active']:
                if block['fall_delay'] > 0:
                    block['fall_delay'] -= 1
                    continue
                
                block['fall_speed'] += random.uniform(0.5, 0.8)
                block['rotation'] += block['rotate_speed']
                block['rotate_speed'] *= 0.995
                block['x'] += block['horizontal_speed']
                block['y'] += block['fall_speed']
                
                if (block['y'] > pyxel.height or 
                    block['x'] < -self.block_width * 2 or 
                    block['x'] > pyxel.width + self.block_width * 2):
                    block['active'] = False

        if self.paddle_exit_started:
            self.paddle_exit_speed *= 1.1
            self.paddle_x += self.paddle_exit_speed
            self.paddle_opacity = max(0, self.paddle_opacity - 0.05)

    def update_paddle(self):
        last_x = self.paddle_x
        if TOUCH_CONTROL:
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.is_touching = True
            if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                self.is_touching = False
            
            if self.is_touching:
                target_x = pyxel.mouse_x - self.paddle_width / 2
                dx = (target_x - self.paddle_x) * 0.2
                self.paddle_x = max(0, min(self.paddle_x + dx, pyxel.width - self.paddle_width))
        else:
            if pyxel.btn(pyxel.KEY_RIGHT):
                self.paddle_x = min(self.paddle_x + 4, pyxel.width - self.paddle_width)
            if pyxel.btn(pyxel.KEY_LEFT):
                self.paddle_x = max(self.paddle_x - 4, 0)

        if abs(self.paddle_x - last_x) > 0.5:
            self.paddle_trail.insert(0, self.paddle_x)
            if len(self.paddle_trail) > self.max_paddle_trail:
                self.paddle_trail.pop()
        elif len(self.paddle_trail) > 0:
            self.paddle_trail = self.paddle_trail[:-1]

    def check_collisions(self):
        for ball in self.balls:
            hit_paddle = False
            blocks_destroyed = 0
            destroyed_block_positions = []
            destroyed_block_colors = []
            
            if (ball.y + ball.size > self.paddle_y and 
                ball.x + ball.size > self.paddle_x and 
                ball.x < self.paddle_x + self.paddle_width):
                hit_paddle = True
                self.current_combo = 0
                self.combo_timer = 0
            
            for i, block in enumerate(self.blocks):
                if block['active']:
                    if (ball.x + ball.size > block['x'] and 
                        ball.x < block['x'] + self.block_width and
                        ball.y + ball.size > block['y'] and 
                        ball.y < block['y'] + self.block_height):
                        
                        block['active'] = False
                        ball.dy *= -1
                        blocks_destroyed += 1
                        
                        center_x = block['x'] + self.block_width / 2
                        center_y = block['y'] + self.block_height / 2
                        destroyed_block_positions.append((center_x, center_y))
                        color = 8 + (i // 14) % 7
                        destroyed_block_colors.append(color)
                        
                        if random.random() < 0.08:
                            self.items.append(Item(
                                block['x'] + self.block_width/2,
                                block['y'] + self.block_height/2
                            ))
            
            if blocks_destroyed > 0:
                # 現在のコンボ数を更新
                old_combo = self.current_combo
                self.current_combo += blocks_destroyed
                
                # 新しいコンボによるボーナス時間を計算
                old_bonus = old_combo * 0.1 if old_combo >= 2 else 0
                new_bonus = self.current_combo * 0.1 if self.current_combo >= 2 else 0
                combo_bonus = new_bonus - old_bonus  # 増分のみを加算
                
                if self.current_combo > self.max_combo:
                    self.max_combo = self.current_combo
                self.combo_timer = self.max_combo_timer
                
                # コンボボーナスを累積
                if self.current_combo >= 2:
                    self.total_combo_bonus += combo_bonus
                
                for (pos_x, pos_y), color in zip(destroyed_block_positions, destroyed_block_colors):
                    self.explosion_effects.append(
                        ExplosionEffect(pos_x, pos_y, self.current_combo)
                    )
                    if self.current_combo >= 2:
                        if self.current_combo == 2:
                            num_particles = 6
                        elif self.current_combo == 3:
                            num_particles = 10
                        elif self.current_combo == 4:
                            num_particles = 15
                        else:
                            num_particles = self.current_combo * 4
                        self.create_particles(pos_x - self.block_width/2, pos_y - self.block_height/2, color, num_particles)
                
                if self.current_combo >= 2:
                    self.combo_text['text'] = f"{self.current_combo} COMBO!"
                    self.combo_text['x'] = ball.x - 20
                    self.combo_text['y'] = ball.y - 10
                    self.combo_text['timer'] = 30
                    
                    self.add_screen_shake(self.current_combo)
            
            if hit_paddle and blocks_destroyed == 0:
                self.current_combo = 0

    def add_new_ball(self):
        if self.balls:
            source_ball = random.choice(self.balls)
            self.balls.append(Ball(source_ball.x, source_ball.y))

    def draw_rotated_block(self, x, y, width, height, color, angle):
        center_x = x + width / 2
        center_y = y + height / 2
        
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        corners = [
            (-width/2, -height/2),
            (width/2, -height/2),
            (width/2, height/2),
            (-width/2, height/2)
        ]
        
        rotated = []
        for corner_x, corner_y in corners:
            rx = corner_x * cos_a - corner_y * sin_a + center_x
            ry = corner_x * sin_a + corner_y * cos_a + center_y
            rotated.append((rx, ry))
        
        pyxel.tri(
            rotated[0][0], rotated[0][1],
            rotated[1][0], rotated[1][1],
            rotated[2][0], rotated[2][1],
            color
        )
        pyxel.tri(
            rotated[0][0], rotated[0][1],
            rotated[2][0], rotated[2][1],
            rotated[3][0], rotated[3][1],
            color
        )

    def create_particles(self, x, y, color, num_particles):
        for _ in range(num_particles):
            self.particles.append(Particle(
                x + random.uniform(0, self.block_width),
                y + random.uniform(0, self.block_height),
                color
            ))

App() 