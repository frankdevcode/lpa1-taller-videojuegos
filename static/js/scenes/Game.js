class Game extends Phaser.Scene {
    constructor() {
        super('Game');
        // Configuración del nivel
        this.levelWidth = 3000; // Ancho del nivel (más largo que la pantalla)
        this.currentLevel = 1;
    }

    create() {
        // Variables del juego
        this.score = 0;
        this.health = 100;
        this.isGameOver = false;
        this.hasWeapon = false;
        this.weaponPower = 10;
        
        // Crear un mundo más grande que la pantalla
        this.physics.world.setBounds(0, 0, this.levelWidth, this.cameras.main.height);
        
        // Agregar fondo (extendido para el nivel)
        const bg = this.add.tileSprite(0, 0, this.levelWidth, this.cameras.main.height, 'background-dungeon');
        bg.setOrigin(0, 0);
        
        // Crear plataformas
        this.platforms = this.physics.add.staticGroup();
        
        // Plataforma base (suelo a lo largo del nivel)
        for (let x = 0; x < this.levelWidth; x += 200) {
            this.platforms.create(x, this.cameras.main.height - 32, 'button')
                .setScale(5, 2)
                .refreshBody();
        }
        
        // Algunas plataformas flotantes distribuidas por el nivel
        this.createPlatform(300, 400, 4);
        this.createPlatform(600, 320, 4);
        this.createPlatform(900, 250, 3);
        this.createPlatform(1200, 400, 4);
        this.createPlatform(1500, 300, 3);
        this.createPlatform(1800, 350, 4);
        this.createPlatform(2100, 250, 3);
        this.createPlatform(2400, 400, 5);
        this.createPlatform(2700, 300, 4);
        
        // Crear jugador usando gráficos primitivos
        this.player = this.physics.add.sprite(100, 450, 'button');
        this.player.setScale(0.5);
        this.player.setTint(0x00ff00); // Color verde para el jugador
        this.player.setBounce(0.2);
        this.player.setCollideWorldBounds(true);
        
        // Seguimiento de cámara al jugador
        this.cameras.main.setBounds(0, 0, this.levelWidth, this.cameras.main.height);
        this.cameras.main.startFollow(this.player, true, 0.1, 0.1);
        
        // Colisión con plataformas
        this.physics.add.collider(this.player, this.platforms);
        
        // Controles
        this.cursors = this.input.keyboard.createCursorKeys();
        this.attackKey = this.input.keyboard.addKey('Z');
        
        // Objetos del juego
        this.setupCoins();
        this.setupEnemies();
        this.setupWeapons();
        this.setupTraps();
        this.setupTreasures();
        
        // Proyectiles
        this.projectiles = this.physics.add.group();
        this.physics.add.collider(this.projectiles, this.platforms, this.handleProjectileHitPlatform, null, this);
        this.physics.add.overlap(this.projectiles, this.enemies, this.handleProjectileHitEnemy, null, this);
        
        // Interfaz de usuario
        this.setupUI();
        
        // Nivel final
        this.createLevelEnd();
    }

    createPlatform(x, y, scale) {
        const platform = this.platforms.create(x, y, 'button');
        platform.setScale(scale, 0.5);
        platform.refreshBody();
        return platform;
    }
    
    setupCoins() {
        // Crear monedas simples
        this.coins = this.physics.add.group();
        
        // Posiciones de las monedas (distribuidas por el nivel)
        const coinPositions = [
            {x: 200, y: 300}, {x: 350, y: 300}, {x: 500, y: 200}, {x: 700, y: 250},
            {x: 900, y: 150}, {x: 1100, y: 300}, {x: 1300, y: 350}, {x: 1500, y: 200},
            {x: 1700, y: 250}, {x: 1900, y: 150}, {x: 2100, y: 100}, {x: 2300, y: 350},
            {x: 2500, y: 250}, {x: 2700, y: 200}, {x: 2900, y: 300}
        ];
        
        coinPositions.forEach(pos => {
            const coin = this.coins.create(pos.x, pos.y, 'button');
            coin.setScale(0.3);
            coin.setTint(0xffff00); // Amarillo para las monedas
            coin.setBounceY(Phaser.Math.FloatBetween(0.4, 0.8));
        });
        
        // Colisión de monedas con plataformas
        this.physics.add.collider(this.coins, this.platforms);
        
        // Recolección de monedas
        this.physics.add.overlap(this.player, this.coins, this.collectCoin, null, this);
    }
    
    setupEnemies() {
        // Crear enemigos
        this.enemies = this.physics.add.group();
        
        // Posiciones de los enemigos (distribuidos estratégicamente)
        const enemyPositions = [
            {x: 600, y: 200, type: 'ground'}, {x: 1200, y: 300, type: 'flying'},
            {x: 1600, y: 200, type: 'ground'}, {x: 2000, y: 100, type: 'flying'},
            {x: 2400, y: 300, type: 'ground'}, {x: 2800, y: 150, type: 'flying'}
        ];
        
        enemyPositions.forEach(pos => {
            const enemy = this.enemies.create(pos.x, pos.y, 'button');
            enemy.type = pos.type;
            
            if (pos.type === 'ground') {
                enemy.setScale(0.4);
                enemy.setTint(0xff0000); // Rojo para enemigos terrestres
                enemy.setBounce(0.2);
                enemy.setCollideWorldBounds(true);
                enemy.setVelocityX(Phaser.Math.Between(-70, 70));
            } else {
                enemy.setScale(0.35);
                enemy.setTint(0xff00ff); // Magenta para enemigos voladores
                enemy.setBounce(0.2);
                enemy.setCollideWorldBounds(true);
                enemy.setVelocityX(Phaser.Math.Between(-100, 100));
                enemy.setGravityY(-250); // Menos gravedad para que "flote"
            }
        });
        
        // Colisión de enemigos con plataformas
        this.physics.add.collider(this.enemies, this.platforms);
        
        // Colisión jugador con enemigos
        this.physics.add.overlap(this.player, this.enemies, this.hitEnemy, null, this);
    }
    
    setupWeapons() {
        // Crear armas
        this.weapons = this.physics.add.group();
        
        // Posiciones de las armas
        const weaponPositions = [
            {x: 800, y: 200, power: 10}, {x: 1800, y: 200, power: 20}
        ];
        
        weaponPositions.forEach(pos => {
            const weapon = this.weapons.create(pos.x, pos.y, 'button');
            weapon.setScale(0.4);
            weapon.setTint(0x0000ff); // Azul para armas
            weapon.power = pos.power;
            weapon.setBounceY(0.2);
        });
        
        // Colisión de armas con plataformas
        this.physics.add.collider(this.weapons, this.platforms);
        
        // Recolección de armas
        this.physics.add.overlap(this.player, this.weapons, this.collectWeapon, null, this);
    }
    
    setupTraps() {
        // Crear trampas
        this.traps = this.physics.add.group();
        
        // Posiciones de las trampas
        const trapPositions = [
            {x: 1000, y: 650}, {x: 1400, y: 650}, {x: 2200, y: 650}
        ];
        
        trapPositions.forEach(pos => {
            const trap = this.traps.create(pos.x, pos.y, 'button');
            trap.setScale(0.5);
            trap.setTint(0xff6600); // Naranja para trampas
            trap.setImmovable(true);
        });
        
        // Interacción con trampas
        this.physics.add.overlap(this.player, this.traps, this.triggerTrap, null, this);
    }
    
    setupTreasures() {
        // Crear tesoros
        this.treasures = this.physics.add.group();
        
        // Posiciones de los tesoros
        const treasurePositions = [
            {x: 1500, y: 200, value: 50}, {x: 2500, y: 300, value: 100}
        ];
        
        treasurePositions.forEach(pos => {
            const treasure = this.treasures.create(pos.x, pos.y, 'button');
            treasure.setScale(0.5);
            treasure.setTint(0xffd700); // Dorado para tesoros
            treasure.value = pos.value;
        });
        
        // Colisión de tesoros con plataformas
        this.physics.add.collider(this.treasures, this.platforms);
        
        // Recolección de tesoros
        this.physics.add.overlap(this.player, this.treasures, this.collectTreasure, null, this);
    }
    
    createLevelEnd() {
        // Crear portal al final del nivel
        this.levelEnd = this.physics.add.sprite(this.levelWidth - 100, this.cameras.main.height - 100, 'button');
        this.levelEnd.setScale(1);
        this.levelEnd.setTint(0x00ffff); // Cyan para el portal
        
        // Colisión con plataformas
        this.physics.add.collider(this.levelEnd, this.platforms);
        
        // Interacción con el portal
        this.physics.add.overlap(this.player, this.levelEnd, this.completeLevel, null, this);
    }
    
    setupUI() {
        // Grupo de UI que sigue la cámara
        this.uiGroup = this.add.group();
        
        // Textos de puntuación y salud
        this.scoreText = this.add.text(16, 16, 'Puntos: 0', { fontSize: '32px', fill: '#fff' });
        this.healthText = this.add.text(16, 50, 'Salud: 100', { fontSize: '32px', fill: '#fff' });
        this.weaponText = this.add.text(16, 84, 'Arma: Ninguna', { fontSize: '32px', fill: '#fff' });
        
        // Añadir textos al grupo UI
        this.uiGroup.add(this.scoreText);
        this.uiGroup.add(this.healthText);
        this.uiGroup.add(this.weaponText);
        
        // Hacer que los elementos de UI sigan la cámara
        this.scoreText.setScrollFactor(0);
        this.healthText.setScrollFactor(0);
        this.weaponText.setScrollFactor(0);
        
        // Instrucciones de juego
        const instructionsText = this.add.text(
            this.cameras.main.width / 2, 
            100, 
            'Controles: Flechas ← → para moverse, ↑ para saltar, Z para atacar\nLlega al portal al final del nivel', 
            { fontSize: '20px', fill: '#fff', align: 'center' }
        );
        instructionsText.setOrigin(0.5);
        instructionsText.setScrollFactor(0);
    }

    update() {
        // Si el juego ha terminado, no actualizar
        if (this.isGameOver) return;
        
        // Controles del jugador
        if (this.cursors.left.isDown) {
            this.player.setVelocityX(-160);
        } else if (this.cursors.right.isDown) {
            this.player.setVelocityX(160);
        } else {
            this.player.setVelocityX(0);
        }

        // Saltar solo si está tocando el suelo
        if (this.cursors.up.isDown && this.player.body.touching.down) {
            this.player.setVelocityY(-330);
        }
        
        // Atacar
        if (Phaser.Input.Keyboard.JustDown(this.attackKey) && this.hasWeapon) {
            this.attackWithWeapon();
        }
        
        // Lógica de los enemigos
        this.enemies.children.iterate((enemy) => {
            if (!enemy.active) return;
            
            // Lógica según el tipo de enemigo
            if (enemy.type === 'ground') {
                // Cambiar dirección al tocar los bordes o al azar
                if (enemy.body.velocity.x > 0 && enemy.body.blocked.right || 
                    enemy.body.velocity.x < 0 && enemy.body.blocked.left) {
                    enemy.setVelocityX(-enemy.body.velocity.x);
                }
            } else if (enemy.type === 'flying') {
                // Movimiento ondulante para enemigos voladores
                enemy.y = enemy.y + Math.sin(this.time.now / 500) * 1.5;
                
                // Cambiar dirección ocasionalmente
                if (Phaser.Math.Between(0, 100) < 1) {
                    enemy.setVelocityX(-enemy.body.velocity.x);
                }
            }
        });
    }

    attackWithWeapon() {
        // Crear proyectil
        const direction = this.player.flipX ? -1 : 1;
        const projectile = this.projectiles.create(
            this.player.x + (direction * 20), 
            this.player.y, 
            'button'
        );
        
        projectile.setScale(0.3);
        projectile.setTint(0x0088ff); // Azul claro para proyectiles
        projectile.setVelocityX(direction * 400);
        projectile.body.allowGravity = false;
        projectile.power = this.weaponPower;
        
        // Autodestrucción después de cierto tiempo
        this.time.delayedCall(1500, () => {
            if (projectile.active) {
                projectile.destroy();
            }
        });
    }

    collectCoin(player, coin) {
        coin.disableBody(true, true);
        
        // Aumentar puntuación
        this.score += 10;
        this.scoreText.setText('Puntos: ' + this.score);
    }
    
    collectWeapon(player, weapon) {
        weapon.disableBody(true, true);
        
        // Obtener o mejorar arma
        this.hasWeapon = true;
        this.weaponPower = weapon.power;
        this.weaponText.setText('Arma: Nivel ' + (this.weaponPower/10));
        
        // Efecto visual
        this.player.setTint(0x66ff66); // Verde más brillante con arma
    }
    
    collectTreasure(player, treasure) {
        treasure.disableBody(true, true);
        
        // Aumentar puntuación considerablemente
        this.score += treasure.value;
        this.scoreText.setText('Puntos: ' + this.score);
        
        // Efecto visual
        this.cameras.main.flash(500, 255, 215, 0); // Flash dorado
    }
    
    triggerTrap(player, trap) {
        trap.disableBody(true, true);
        
        // Crear efecto de explosión
        const explosion = this.add.circle(trap.x, trap.y, 50, 0xff0000, 0.7);
        
        // Daño al jugador
        this.health -= 30;
        this.healthText.setText('Salud: ' + this.health);
        
        // Efecto de rebote
        this.player.setVelocity(Phaser.Math.Between(-150, 150), -200);
        
        // Efecto visual
        this.cameras.main.shake(300, 0.03);
        
        // Eliminar explosión después de un tiempo
        this.time.delayedCall(300, () => {
            explosion.destroy();
        });
        
        // Verificar si el jugador ha perdido
        if (this.health <= 0) {
            this.gameOver();
        }
    }
    
    handleProjectileHitPlatform(projectile, platform) {
        projectile.destroy();
    }
    
    handleProjectileHitEnemy(projectile, enemy) {
        // Eliminar proyectil
        projectile.destroy();
        
        // Eliminar enemigo
        enemy.disableBody(true, true);
        
        // Aumentar puntuación
        this.score += 15;
        this.scoreText.setText('Puntos: ' + this.score);
        
        // Efecto visual
        const explosion = this.add.circle(enemy.x, enemy.y, 30, 0xff8800, 0.7);
        this.time.delayedCall(200, () => {
            explosion.destroy();
        });
    }
    
    hitEnemy(player, enemy) {
        // Si el jugador cae sobre el enemigo, lo elimina
        if (player.y < enemy.y - player.height / 2) {
            enemy.disableBody(true, true);
            this.score += 20;
            this.scoreText.setText('Puntos: ' + this.score);
            player.setVelocityY(-200);
        } else {
            // El enemigo daña al jugador
            this.health -= 15;
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
    
    completeLevel() {
        this.isGameOver = true;
        
        // Detener física
        this.physics.pause();
        
        // Cambiar color del jugador
        this.player.setTint(0x00ffff);
        
        // Mostrar mensaje de nivel completado
        const victoryText = this.add.text(
            this.cameras.main.width / 2 + this.cameras.main.scrollX, 
            this.cameras.main.height / 2, 
            '¡NIVEL COMPLETADO!', 
            { fontSize: '48px', fill: '#00ff00', fontStyle: 'bold' }
        );
        victoryText.setOrigin(0.5);
        
        // Mostrar puntuación final
        const finalScoreText = this.add.text(
            this.cameras.main.width / 2 + this.cameras.main.scrollX, 
            this.cameras.main.height / 2 + 60, 
            'Puntuación final: ' + this.score, 
            { fontSize: '32px', fill: '#ffffff' }
        );
        finalScoreText.setOrigin(0.5);
        
        // Botón para volver al menú
        const menuButton = this.add.image(
            this.cameras.main.width / 2 + this.cameras.main.scrollX, 
            this.cameras.main.height / 2 + 140, 
            'button'
        );
        menuButton.setScale(2);
        menuButton.setInteractive();
        
        const menuText = this.add.text(
            this.cameras.main.width / 2 + this.cameras.main.scrollX, 
            this.cameras.main.height / 2 + 140, 
            'Volver al menú', 
            { fontSize: '24px', fill: '#fff' }
        );
        menuText.setOrigin(0.5);
        
        menuButton.on('pointerdown', () => {
            this.scene.start('MainMenu');
        });
    }
    
    gameOver() {
        this.isGameOver = true;
        
        // Detener física
        this.physics.pause();
        
        // Cambiar color del jugador
        this.player.setTint(0xff0000);
        
        // Mostrar mensaje de game over
        const gameOverText = this.add.text(
            this.cameras.main.width / 2 + this.cameras.main.scrollX, 
            this.cameras.main.height / 2, 
            'GAME OVER', 
            { fontSize: '64px', fill: '#ff0000', fontStyle: 'bold' }
        );
        gameOverText.setOrigin(0.5);
        
        // Botones para reiniciar o volver al menú
        const restartButton = this.add.image(
            this.cameras.main.width / 2 + this.cameras.main.scrollX - 100, 
            this.cameras.main.height / 2 + 100, 
            'button'
        );
        restartButton.setScale(1.5);
        restartButton.setInteractive();
        
        const restartText = this.add.text(
            this.cameras.main.width / 2 + this.cameras.main.scrollX - 100, 
            this.cameras.main.height / 2 + 100, 
            'Reiniciar', 
            { fontSize: '24px', fill: '#fff' }
        );
        restartText.setOrigin(0.5);
        
        const menuButton = this.add.image(
            this.cameras.main.width / 2 + this.cameras.main.scrollX + 100, 
            this.cameras.main.height / 2 + 100, 
            'button'
        );
        menuButton.setScale(1.5);
        menuButton.setInteractive();
        
        const menuText = this.add.text(
            this.cameras.main.width / 2 + this.cameras.main.scrollX + 100, 
            this.cameras.main.height / 2 + 100, 
            'Menú', 
            { fontSize: '24px', fill: '#fff' }
        );
        menuText.setOrigin(0.5);
        
        restartButton.on('pointerdown', () => {
            this.scene.restart();
        });
        
        menuButton.on('pointerdown', () => {
            this.scene.start('MainMenu');
        });
    }
} 