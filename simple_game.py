import pyxel
import math
import random
import time

TOUCH_CONTROL = True  # タッチ操作の有効化フラグ

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        # より広い範囲の速度とより多様な方向を設定
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1.5, 4.0)  # 速度範囲を広げる
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.life = 30  # パーティクルの寿命（フレーム数）
        self.size = 1   # パーティクルのサイズ

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
        
        # 画面端での跳ね返り処理を改善
        if next_x < 0:
            self.x = 0
            self.dx = abs(self.dx)  # 必ず右向きに
        elif next_x > pyxel.width - self.size:
            self.x = pyxel.width - self.size
            self.dx = -abs(self.dx)  # 必ず左向きに
        else:
            self.x = next_x
            
        if next_y < 0:
            self.y = 0
            self.dy = abs(self.dy)  # 必ず下向きに
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
        # 残像を描画（後ろの位置ほど薄く）
        for i, (trail_x, trail_y) in enumerate(self.trail_positions[1:], 1):
            alpha = (self.max_trail - i) / self.max_trail  # 透明度を計算
            color = 1 if i > self.max_trail // 2 else 5  # 残像の色を変化させる
            pyxel.rect(trail_x, trail_y, self.size, self.size, color)
        
        # 現在位置のボールを描画
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
        # 点滅効果でアイテムを目立たせる
        if pyxel.frame_count % 30 < 15:
            color = 11  # 水色
        else:
            color = 10  # 黄色
        pyxel.rect(self.x, self.y, self.size, self.size, color)

class ExplosionEffect:
    def __init__(self, x, y, combo):
        self.x = x
        self.y = y
        self.combo = combo
        self.life = 8  # エフェクトの持続フレームを15から8に短縮
        self.max_life = 8
        # コンボ数に応じて最大半径を設定（さらに大きな変化に）
        base_radius = 12  # 基本半径を大きく
        combo_bonus = combo * 6  # コンボごとに6ピクセルずつ増加（2倍に）
        self.max_radius = min(base_radius + combo_bonus, 60)  # 最大半径を60に設定（1.5倍に）
        
    def update(self):
        self.life -= 1
        return self.life > 0
    
    def get_current_radius(self):
        progress = self.life / self.max_life
        # イージング関数（ease-out-in）をより急速に
        if progress > 0.4:  # 拡大フェーズの時間を短く（0.5→0.4）
            # 拡大フェーズ（ease-out-quartic）
            t = (1 - progress) / 0.6  # 0.6で割って正規化
            return self.max_radius * (1 - (1 - t) * (1 - t) * (1 - t) * (1 - t))
        else:
            # 縮小フェーズ（ease-in-quartic）
            t = progress / 0.4  # 0.4で割って正規化
            return self.max_radius * (t * t * t * t)
    
    def draw(self):
        radius = self.get_current_radius()
        # 軌跡の数（コンボ数に応じて増加、より多く）
        num_trails = min(self.combo * 4 + 8, 32)  # 基本8本、コンボごとに4本増加、最大32本
        
        # 軌跡を描画（薄い色で）
        for i in range(num_trails):
            angle = (i / num_trails) * math.pi * 2
            trail_x = self.x + math.cos(angle) * radius
            trail_y = self.y + math.sin(angle) * radius
            # コンボ数に応じて色を変える（3以上で黄色系、それ以外は白系）
            color = 10 if self.combo >= 3 else 6
            pyxel.pset(trail_x, trail_y, color)

        # 中心点を描画（より大きく）
        center_color = 7 if self.combo < 3 else 10
        center_size = min(1 + self.combo // 2, 4)  # 中心点のサイズを調整（最大4）
        pyxel.circ(self.x, self.y, center_size, center_color)

class App:
    def __init__(self):
        pyxel.init(160, 120, title="Break the blocks")
        self.touch_x = 0  # タッチ位置X
        self.is_touching = False  # タッチ中フラグ
        self.init_game()
        pyxel.run(self.update, self.draw)
    
    def init_game(self):
        self.paddle_x = 80
        self.paddle_width = 24
        self.paddle_height = 2
        self.paddle_y = 110
        self.paddle_trail = []
        self.max_paddle_trail = 6
        self.paddle_opacity = 1.0  # パドルの不透明度
        self.paddle_exit_started = False  # パドル退散フラグ
        self.paddle_exit_speed = 0  # パドルの退散速度
        
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
                    'rotation': 0,  # 回転角度
                    'rotate_speed': 0,  # 回転速度
                    'fall_delay': 0,  # 落下開始の遅延
                    'horizontal_speed': 0  # 横方向の移動速度
                })
        
        self.particles = []
        self.items = []
        self.game_cleared = False
        self.game_over = False  # ゲームオーバー状態を追加
        self.game_over_timer = 0  # ゲームオーバーエフェクトのタイマー
        self.clear_message_y = 60
        self.start_time = time.time()
        self.clear_time = 0
        self.bonus_time = 0
        
        self.current_combo = 0
        self.combo_timer = 0
        self.max_combo_timer = 30
        self.screen_shake = {'x': 0, 'y': 0, 'duration': 0, 'magnitude': 0}
        self.combo_text = {'text': '', 'x': 0, 'y': 0, 'timer': 0}
        self.explosion_effects = []

    def update_screen_shake(self):
        if self.screen_shake['duration'] > 0:
            magnitude = self.screen_shake['magnitude']
            # 小数点のマグニチュードに対応するため、ランダム値を調整
            if magnitude < 1:
                # 0.5ピクセルの場合、50%の確率で1ピクセル、50%の確率で0ピクセル
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
        # コンボ数に応じて画面の揺れの強さと持続時間を設定
        if combo >= 2:
            if combo == 2:
                magnitude = 0.5  # 0.5ピクセル
                duration = 1
            elif combo == 3:
                magnitude = 1
                duration = 3
            elif combo == 4:
                magnitude = 2
                duration = 5
            else:  # 5コンボ以上
                magnitude = 3
                duration = 8
            
            self.screen_shake['magnitude'] = magnitude
            self.screen_shake['duration'] = duration

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
                remaining_balls = len(self.balls)
                if remaining_balls > 1:
                    self.bonus_time = remaining_balls - 1
                    self.clear_time = max(0, self.clear_time - self.bonus_time)
                else:
                    self.bonus_time = 0
            self.game_cleared = True

    def start_game_over(self):
        self.game_over = True
        self.game_over_timer = 0
        # 画面シェイクを設定
        self.screen_shake['magnitude'] = 3
        self.screen_shake['duration'] = 8
        
        # パドルの退散を即座に開始
        self.paddle_exit_started = True
        self.paddle_exit_speed = 1  # 初期退散速度
        
        # アクティブなブロックに初期パラメータを設定
        for block in self.blocks:
            if block['active']:
                # さらに速い初期落下速度
                block['fall_speed'] = random.uniform(2.0, 4.0)
                # 30%の確率でブロックを回転させる
                if random.random() < 0.3:
                    block['rotate_speed'] = random.uniform(-15, 15)
                # より短い落下開始遅延
                block['fall_delay'] = random.randint(0, 20)
                # 50%の確率で横方向の移動を追加（より大きな移動速度）
                if random.random() < 0.5:
                    block['horizontal_speed'] = random.uniform(-1.5, 1.5)

    def update_game_over(self):
        self.game_over_timer += 1
        
        # 画面シェイクの更新
        if self.screen_shake['duration'] > 0:
            magnitude = self.screen_shake['magnitude']
            self.screen_shake['x'] = random.randint(-magnitude, magnitude)
            self.screen_shake['y'] = random.randint(-magnitude, magnitude)
            self.screen_shake['duration'] -= 1
        else:
            self.screen_shake['x'] = 0
            self.screen_shake['y'] = 0
            self.screen_shake['magnitude'] = 0
        
        # ブロックの落下処理
        for block in self.blocks:
            if block['active']:
                # 落下遅延がある場合は待機
                if block['fall_delay'] > 0:
                    block['fall_delay'] -= 1
                    continue
                
                # 落下速度を徐々に加速（さらに大きな加速度）
                block['fall_speed'] += random.uniform(0.5, 0.8)
                
                # 回転の更新
                block['rotation'] += block['rotate_speed']
                # 回転速度の減衰を緩やかに
                block['rotate_speed'] *= 0.995
                
                # 横方向の移動を適用
                block['x'] += block['horizontal_speed']
                
                # ブロックを落下させる
                block['y'] += block['fall_speed']
                
                # 画面外に出たブロックを非アクティブにする
                if (block['y'] > pyxel.height or 
                    block['x'] < -self.block_width * 2 or 
                    block['x'] > pyxel.width + self.block_width * 2):
                    block['active'] = False

        # パドルの退散処理
        if self.paddle_exit_started:
            # 徐々に加速しながら右に移動
            self.paddle_exit_speed *= 1.1
            self.paddle_x += self.paddle_exit_speed
            # 不透明度を下げる
            self.paddle_opacity = max(0, self.paddle_opacity - 0.05)

    def create_particles(self, x, y, color, num_particles):
        for _ in range(num_particles):
            self.particles.append(Particle(
                x + random.uniform(0, self.block_width),
                y + random.uniform(0, self.block_height),
                color
            ))

    def update_paddle(self):
        # 現在のパドル位置を履歴に追加
        self.paddle_trail.insert(0, self.paddle_x)
        if len(self.paddle_trail) > self.max_paddle_trail:
            self.paddle_trail.pop()

        if TOUCH_CONTROL:
            # タッチ操作の処理
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                self.is_touching = True
            if pyxel.btnr(pyxel.MOUSE_BUTTON_LEFT):
                self.is_touching = False
            
            if self.is_touching:
                target_x = pyxel.mouse_x - self.paddle_width / 2
                # パドルの移動を滑らかにする
                dx = (target_x - self.paddle_x) * 0.2
                self.paddle_x = max(0, min(self.paddle_x + dx, pyxel.width - self.paddle_width))
        else:
            # キーボード操作
            if pyxel.btn(pyxel.KEY_RIGHT):
                self.paddle_x = min(self.paddle_x + 4, pyxel.width - self.paddle_width)
            if pyxel.btn(pyxel.KEY_LEFT):
                self.paddle_x = max(self.paddle_x - 4, 0)

    def check_collisions(self):
        for ball in self.balls:
            hit_paddle = False
            blocks_destroyed = 0
            destroyed_block_positions = []
            destroyed_block_colors = []
            
            # パドルとの衝突をチェック
            if (ball.y + ball.size > self.paddle_y and 
                ball.x + ball.size > self.paddle_x and 
                ball.x < self.paddle_x + self.paddle_width):
                hit_paddle = True
                self.current_combo = 0
                self.combo_timer = 0
            
            # ブロックとの衝突をチェック
            for i, block in enumerate(self.blocks):
                if block['active']:
                    if (ball.x + ball.size > block['x'] and 
                        ball.x < block['x'] + self.block_width and
                        ball.y + ball.size > block['y'] and 
                        ball.y < block['y'] + self.block_height):
                        
                        block['active'] = False
                        ball.dy *= -1
                        blocks_destroyed += 1
                        
                        # 破壊されたブロックの中心位置と色を保存
                        center_x = block['x'] + self.block_width / 2
                        center_y = block['y'] + self.block_height / 2
                        destroyed_block_positions.append((center_x, center_y))
                        color = 8 + (i // 14) % 7
                        destroyed_block_colors.append(color)
                        
                        # アイテムの生成（8%の確率）
                        if random.random() < 0.08:
                            self.items.append(Item(
                                block['x'] + self.block_width/2,
                                block['y'] + self.block_height/2
                            ))
            
            # ブロックを破壊した場合のコンボ処理
            if blocks_destroyed > 0:
                self.current_combo += blocks_destroyed
                self.combo_timer = self.max_combo_timer
                
                # 各破壊されたブロックの位置に爆発エフェクトとパーティクルを追加
                for (pos_x, pos_y), color in zip(destroyed_block_positions, destroyed_block_colors):
                    self.explosion_effects.append(
                        ExplosionEffect(pos_x, pos_y, self.current_combo)
                    )
                    # コンボ数に応じてパーティクル数を設定
                    if self.current_combo >= 2:
                        # 新しいコンボ数に応じたパーティクル数
                        if self.current_combo == 2:
                            num_particles = 6
                        elif self.current_combo == 3:
                            num_particles = 10
                        elif self.current_combo == 4:
                            num_particles = 15
                        else:  # 5コンボ以上
                            num_particles = self.current_combo * 4  # コンボ数×4個
                        self.create_particles(pos_x - self.block_width/2, pos_y - self.block_height/2, color, num_particles)
                
                # コンボテキストの設定
                if self.current_combo >= 2:
                    self.combo_text['text'] = f"{self.current_combo} COMBO!"
                    self.combo_text['x'] = ball.x - 20
                    self.combo_text['y'] = ball.y - 10
                    self.combo_text['timer'] = 30
                    
                    # 画面シェイク
                    self.add_screen_shake(self.current_combo)
            
            # パドルに当たった後にブロックを壊していない場合はコンボリセット
            if hit_paddle and blocks_destroyed == 0:
                self.current_combo = 0

    def add_new_ball(self):
        # ランダムなボールを既存のボールの位置から生成
        if self.balls:
            source_ball = random.choice(self.balls)
            self.balls.append(Ball(source_ball.x, source_ball.y))

    def draw_rotated_block(self, x, y, width, height, color, angle):
        # ブロックの中心を計算
        center_x = x + width / 2
        center_y = y + height / 2
        
        # 回転した四隅の座標を計算
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        # ブロックの四隅の相対座標
        corners = [
            (-width/2, -height/2),
            (width/2, -height/2),
            (width/2, height/2),
            (-width/2, height/2)
        ]
        
        # 回転後の座標を計算
        rotated = []
        for corner_x, corner_y in corners:
            rx = corner_x * cos_a - corner_y * sin_a + center_x
            ry = corner_x * sin_a + corner_y * cos_a + center_y
            rotated.append((rx, ry))
        
        # 四角形を描画
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

    def draw(self):
        pyxel.cls(0)
        
        shake_x = self.screen_shake['x']
        shake_y = self.screen_shake['y']
        
        if self.game_cleared:
            if pyxel.frame_count % 30 < 20:
                pyxel.text(65 + shake_x, self.clear_message_y - 20 + shake_y, "FINISH!!!", 7)
            
            # オリジナルタイムの表示
            minutes = int(self.clear_time // 60)
            seconds = int(self.clear_time % 60)
            milliseconds = int((self.clear_time * 100) % 100)
            time_text = f"TIME: {minutes:02d}:{seconds:02d}.{milliseconds:02d}"
            pyxel.text(45 + shake_x, self.clear_message_y + shake_y, time_text, 7)
            
            if self.bonus_time > 0:
                bonus_text = f"SPECIAL BONUS! -{self.bonus_time}s ({len(self.balls)} balls)"
                pyxel.text(30 + shake_x, self.clear_message_y + 10 + shake_y, bonus_text, 10)
                
                final_time = self.clear_time - self.bonus_time
                f_minutes = int(final_time // 60)
                f_seconds = int(final_time % 60)
                f_milliseconds = int((final_time * 100) % 100)
                final_text = f"FINAL TIME: {f_minutes:02d}:{f_seconds:02d}.{f_milliseconds:02d}"
                pyxel.text(35 + shake_x, self.clear_message_y + 20 + shake_y, final_text, 11)
            
            if TOUCH_CONTROL:
                pyxel.text(40 + shake_x, self.clear_message_y + 30 + shake_y, "TOUCH TO RESTART", 6)
            else:
                pyxel.text(40 + shake_x, self.clear_message_y + 30 + shake_y, "PRESS SPACE TO RESTART", 6)
            return
        
        if self.game_over:
            # ゲームオーバー時のブロック描画
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
            
            # パドルの残像と本体を不透明度に応じて描画
            if self.paddle_opacity > 0:
                # 残像の描画（不透明度に応じて薄く）
                for i, trail_x in enumerate(self.paddle_trail[1:], 1):
                    alpha = (self.max_paddle_trail - i) / self.max_paddle_trail * self.paddle_opacity
                    if alpha > 0.3:  # ある程度の不透明度がある場合のみ描画
                        color = 1 if i > self.max_paddle_trail // 2 else 5
                        pyxel.rect(trail_x + shake_x, self.paddle_y + shake_y, 
                                self.paddle_width, self.paddle_height, color)
                
                # パドル本体の描画（不透明度に応じて色を変更）
                if self.paddle_opacity > 0.7:
                    color = 7
                elif self.paddle_opacity > 0.4:
                    color = 6
                else:
                    color = 5
                pyxel.rect(self.paddle_x + shake_x, self.paddle_y + shake_y, 
                          self.paddle_width, self.paddle_height, color)
            
            # "OOPS!" テキストを表示（ゲームオーバーから0.5秒後）
            if self.game_over_timer > 30 and (self.game_over_timer // 10) % 2 == 0:
                pyxel.text(70, 50, "OOPS!", 8)
                if self.paddle_opacity <= 0:  # パドルが完全に消えてから
                    pyxel.text(40, 70, "PRESS SPACE TO RESTART", 7)
            return
        
        # パドルの残像を描画
        for i, trail_x in enumerate(self.paddle_trail[1:], 1):
            alpha = (self.max_paddle_trail - i) / self.max_paddle_trail
            color = 1 if i > self.max_paddle_trail // 2 else 5
            pyxel.rect(trail_x + shake_x, self.paddle_y + shake_y, 
                      self.paddle_width, self.paddle_height, color)
        
        # 現在のパドルを描画
        pyxel.rect(self.paddle_x + shake_x, self.paddle_y + shake_y, 
                  self.paddle_width, self.paddle_height, 7)
        
        for ball in self.balls:
            ball.draw()
        
        for i, block in enumerate(self.blocks):
            if block['active']:
                color = 8 + (i // 14) % 7
                pyxel.rect(block['x'] + shake_x, block['y'] + shake_y, 
                          self.block_width, self.block_height, color)
        
        # 爆発エフェクトを描画（パーティクルの前に）
        for effect in self.explosion_effects:
            effect.draw()
        
        for particle in self.particles:
            particle.draw()
        
        for item in self.items:
            item.draw()
        
        # コンボテキストの表示
        if self.combo_text['timer'] > 0:
            color = 10 if self.current_combo >= 3 else 7  # 3コンボ以上で黄色
            pyxel.text(
                self.combo_text['x'] + shake_x,
                self.combo_text['y'] + shake_y,
                self.combo_text['text'],
                color
            )
            self.combo_text['timer'] -= 1

# Pyxel Webのエントリーポイント
App() 