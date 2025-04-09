class Game extends Phaser.Scene {
    constructor() {
        super('Game');
    }

    create() {
        // Variables del juego
        this.score = 0;
        this.health = 100;
        
        // Agregar fondo
        const bg = this.add.image(0, 0, 'background-dungeon');
        bg.setOrigin(0, 0);
        bg.setDisplaySize(this.cameras.main.width, this.cameras.main.height);
        
        // Crear plataformas (estáticas para este ejemplo)
        this.platforms = this.physics.add.staticGroup();
        
        // Plataforma base (suelo)
        this.platforms.create(this.cameras.main.width / 2, this.cameras.main.height - 32, 'button')
            .setScale(20, 2)
            .refreshBody();
        
        // Algunas plataformas flotantes
        this.platforms.create(600, 400, 'button').setScale(4, 0.5).refreshBody();
        this.platforms.create(50, 250, 'button').setScale(4, 0.5).refreshBody();
        this.platforms.create(750, 220, 'button').setScale(4, 0.5).refreshBody();
        
        // Crear jugador
        this.player = this.physics.add.sprite(100, 450, 'player');
        this.player.setBounce(0.2);
        this.player.setCollideWorldBounds(true);
        
        // Colisión con plataformas
        this.physics.add.collider(this.player, this.platforms);
        
        // Controles
        this.cursors = this.input.keyboard.createCursorKeys();
        
        // Crear enemigos
        this.enemies = this.physics.add.group();
        
        // Enemigo terrestre
        const groundEnemy = this.enemies.create(600, 350, 'enemy-ground');
        groundEnemy.setBounce(0.2);
        groundEnemy.setCollideWorldBounds(true);
        groundEnemy.setVelocityX(100);
        groundEnemy.setFlipX(true);
        groundEnemy.type = 'ground';
        groundEnemy.play('enemy-ground-walk');
        
        // Enemigo volador
        const flyingEnemy = this.enemies.create(300, 100, 'enemy-flying');
        flyingEnemy.setBounce(0.2);
        flyingEnemy.setCollideWorldBounds(true);
        flyingEnemy.setGravityY(-300); // Reducir la gravedad para que "flote"
        flyingEnemy.setVelocityX(80);
        flyingEnemy.type = 'flying';
        flyingEnemy.play('enemy-flying-fly');
        
        // Colisión de enemigos con plataformas
        this.physics.add.collider(this.enemies, this.platforms);
        
        // Colisión jugador con enemigos
        this.physics.add.overlap(this.player, this.enemies, this.hitEnemy, null, this);
        
        // Objetos coleccionables
        this.coins = this.physics.add.group({
            key: 'coin',
            repeat: 11,
            setXY: { x: 12, y: 0, stepX: 70 }
        });
        
        this.coins.children.iterate(function (child) {
            child.setBounceY(Phaser.Math.FloatBetween(0.4, 0.8));
        });
        
        // Colisión con monedas
        this.physics.add.collider(this.coins, this.platforms);
        this.physics.add.overlap(this.player, this.coins, this.collectCoin, null, this);
        
        // Trampas (bombas)
        this.bombs = this.physics.add.group();
        
        // Colocar algunas bombas iniciales
        this.createBomb(200, 100);
        this.createBomb(500, 100);
        
        // Colisión con bombas
        this.physics.add.collider(this.bombs, this.platforms);
        this.physics.add.overlap(this.player, this.bombs, this.hitBomb, null, this);
        
        // Interfaz de usuario
        this.scoreText = this.add.text(16, 16, 'Puntos: 0', { fontSize: '32px', fill: '#fff' });
        this.healthText = this.add.text(16, 50, 'Salud: 100', { fontSize: '32px', fill: '#fff' });
    }

    update() {
        // Mover al jugador
        if (this.cursors.left.isDown) {
            this.player.setVelocityX(-160);
            this.player.anims.play('player-walk', true);
            this.player.setFlipX(true);
        } else if (this.cursors.right.isDown) {
            this.player.setVelocityX(160);
            this.player.anims.play('player-walk', true);
            this.player.setFlipX(false);
        } else {
            this.player.setVelocityX(0);
            this.player.anims.play('player-idle', true);
        }

        // Saltar
        if (this.cursors.up.isDown && this.player.body.touching.down) {
            this.player.setVelocityY(-330);
        }
        
        // Lógica de los enemigos
        this.enemies.children.iterate((enemy) => {
            // Cambiar dirección al tocar los bordes
            if (enemy.body.velocity.x > 0 && enemy.x > 800) {
                enemy.setVelocityX(-enemy.body.velocity.x);
                enemy.setFlipX(false);
            } else if (enemy.body.velocity.x < 0 && enemy.x < 100) {
                enemy.setVelocityX(-enemy.body.velocity.x);
                enemy.setFlipX(true);
            }
            
            // Comportamiento específico para enemigos voladores
            if (enemy.type === 'flying') {
                // Movimiento ondulante
                enemy.y = enemy.y + Math.sin(this.time.now / 500) * 1.5;
            }
        });
    }

    collectCoin(player, coin) {
        coin.disableBody(true, true);
        
        // Aumentar puntuación
        this.score += 10;
        this.scoreText.setText('Puntos: ' + this.score);
        
        // Reproducir sonido
        this.sound.play('coin-sound');
        
        // Si todas las monedas han sido recolectadas, crear más
        if (this.coins.countActive(true) === 0) {
            this.coins.children.iterate(function (child) {
                child.enableBody(true, child.x, 0, true, true);
            });
            
            // Crear una bomba adicional
            this.createBomb(Phaser.Math.Between(100, 700), 0);
        }
    }

    createBomb(x, y) {
        const bomb = this.bombs.create(x, y, 'bomb');
        bomb.setBounce(1);
        bomb.setCollideWorldBounds(true);
        bomb.setVelocity(Phaser.Math.Between(-200, 200), 20);
        bomb.allowGravity = true;
    }

    hitBomb(player, bomb) {
        // Efecto de explosión
        this.sound.play('explosion-sound');
        const explosion = this.add.sprite(bomb.x, bomb.y, 'explosion');
        explosion.play('explosion-anim');
        
        // Deshabilitar la bomba
        bomb.disableBody(true, true);
        
        // Reducir salud
        this.health -= 20;
        this.healthText.setText('Salud: ' + this.health);
        
        // Efecto visual
        this.cameras.main.shake(300, 0.02);
        
        // Verificar si el jugador ha perdido
        if (this.health <= 0) {
            this.gameOver();
        }
    }

    hitEnemy(player, enemy) {
        // Si el jugador está por encima del enemigo, lo elimina
        if (player.y < enemy.y - 20) {
            // Derrotar al enemigo
            enemy.disableBody(true, true);
            
            // Animación de magia
            const magic = this.add.sprite(enemy.x, enemy.y, 'magic');
            magic.play('magic-anim');
            
            // Puntos y bonificación de salud
            this.score += 20;
            this.scoreText.setText('Puntos: ' + this.score);
            
            // Salto de rebote
            player.setVelocityY(-200);
        } else {
            // El enemigo daña al jugador
            this.health -= 10;
            this.healthText.setText('Salud: ' + this.health);
            
            // Efecto de rebote
            const direction = player.x < enemy.x ? -1 : 1;
            player.setVelocity(direction * 200, -200);
            
            // Efecto visual
            this.cameras.main.shake(100, 0.01);
            
            // Verificar si el jugador ha perdido
            if (this.health <= 0) {
                this.gameOver();
            }
        }
    }

    gameOver() {
        // Detener juego y regresar al menú
        this.physics.pause();
        this.player.setTint(0xff0000);
        
        // Texto de Game Over
        const gameOverText = this.add.text(this.cameras.main.width / 2, this.cameras.main.height / 2, 'GAME OVER', { 
            font: 'bold 64px Arial', 
            fill: '#ff0000',
            stroke: '#000000',
            strokeThickness: 6
        });
        gameOverText.setOrigin(0.5);
        
        // Texto para reiniciar
        const restartText = this.add.text(this.cameras.main.width / 2, this.cameras.main.height / 2 + 70, 'Haz clic para reiniciar', { 
            font: '32px Arial', 
            fill: '#ffffff',
            stroke: '#000000',
            strokeThickness: 4
        });
        restartText.setOrigin(0.5);
        
        // Agregar evento de clic para reiniciar
        this.input.on('pointerdown', () => {
            this.scene.restart();
        });
    }
} 