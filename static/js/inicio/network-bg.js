(function () {
    const canvas = document.getElementById('inicio-network-canvas');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width, height, cubes;
    let animationId;

    const CONFIG = {
        // Cantidad base de cubos por cada 100,000 px² de área
        densityPer100kPx: 2.5,

        // Tamaño de los cubos (min-max)
        minSize: 18,
        maxSize: 36,

        // Velocidad de flotación
        speed: 0.12,

        // Opacidad general de los elementos
        minOpacity: 0.25,
        maxOpacity: 0.65,

        // Paleta de colores de Constru-Trans
        colorStops: [
            { r: 245, g: 166, b: 35 },   // naranja
            { r: 255, g: 179, b: 71 },   // ámbar/dorado
            { r: 59, g: 130, b: 246 },   // azul acento
            { r: 30, g: 58, b: 95 },     // azul oscuro
        ],
    };

    // Modelo de Vértices de un Cubo Unitario 3D (centrado en 0,0,0)
    const VERTICES = [
        { x: -1, y: -1, z: -1 },
        { x: 1, y: -1, z: -1 },
        { x: 1, y: 1, z: -1 },
        { x: -1, y: 1, z: -1 },
        { x: -1, y: -1, z: 1 },
        { x: 1, y: -1, z: 1 },
        { x: 1, y: 1, z: 1 },
        { x: -1, y: 1, z: 1 }
    ];

    // Conexiones de Aristas
    const EDGES = [
        [0, 1], [1, 2], [2, 3], [3, 0], // Cara Trasera
        [4, 5], [5, 6], [6, 7], [7, 4], // Cara Delantera
        [0, 4], [1, 5], [2, 6], [3, 7]  // Uniones
    ];

    // Índices de Vértices para las 6 Caras (para sombreado semitransparente)
    const FACES = [
        [0, 1, 2, 3], // Atrás
        [4, 5, 6, 7], // Adelante
        [0, 1, 5, 4], // Arriba
        [2, 3, 7, 6], // Abajo
        [0, 3, 7, 4], // Izquierda
        [1, 2, 6, 5]  // Derecha
    ];

    // Estado del mouse y tracking
    let mouse = { x: null, y: null, active: false };

    // ==========================================
    // AJUSTAR CANVAS AL TAMAÑO DE LA ZONA
    // ==========================================

    function resize() {
        const zone = canvas.parentElement;
        if (!zone) return;

        const rect = zone.getBoundingClientRect();
        width = canvas.width = Math.round(rect.width);
        height = canvas.height = Math.round(rect.height);
    }

    // ==========================================
    // INTERPOLAR COLOR SEGÚN POSICIÓN VERTICAL (0 a 1)
    // ==========================================

    function colorAt(t) {
        const stops = CONFIG.colorStops;
        const scaled = t * (stops.length - 1);
        const i = Math.min(Math.floor(scaled), stops.length - 2);
        const localT = scaled - i;

        const a = stops[i];
        const b = stops[i + 1];

        return {
            r: Math.round(a.r + (b.r - a.r) * localT),
            g: Math.round(a.g + (b.g - a.g) * localT),
            b: Math.round(a.b + (b.b - a.b) * localT),
        };
    }

    // Rotación de puntos en 3D
    function rotate3D(point, rx, ry, rz) {
        // Rotar alrededor de X
        const cosX = Math.cos(rx), sinX = Math.sin(rx);
        let y1 = point.y * cosX - point.z * sinX;
        let z1 = point.y * sinX + point.z * cosX;

        // Rotar alrededor de Y
        const cosY = Math.cos(ry), sinY = Math.sin(ry);
        let x2 = point.x * cosY + z1 * sinY;
        let z2 = -point.x * sinY + z1 * cosY;

        // Rotar alrededor de Z
        const cosZ = Math.cos(rz), sinZ = Math.sin(rz);
        let x3 = x2 * cosZ - y1 * sinZ;
        let y3 = x2 * sinZ + y1 * cosZ;

        return { x: x3, y: y3, z: z2 };
    }

    // Proyección con perspectiva
    function project(point, cube) {
        // Distancia virtual de la cámara
        const d = 3.0;
        // z2 oscila entre -1.73 y 1.73. Escalar z para evitar división por cero.
        const perspectiveFactor = 2.2 / (d - point.z * 0.75);
        const halfSize = cube.size / 2;

        return {
            x: cube.x + point.x * halfSize * perspectiveFactor,
            y: cube.y + point.y * halfSize * perspectiveFactor
        };
    }

    // ==========================================
    // CREAR CUBOS
    // ==========================================

    function createCubes() {
        const area = width * height;
        const count = Math.max(
            15,
            Math.round((area / 100000) * CONFIG.densityPer100kPx)
        );

        cubes = [];

        for (let i = 0; i < count; i++) {
            const x = Math.random() * width;
            const y = Math.random() * height;
            
            // Velocidad base
            const vx = (Math.random() - 0.5) * CONFIG.speed;
            const vy = (Math.random() - 0.5) * CONFIG.speed;

            cubes.push({
                x: x,
                y: y,
                size: CONFIG.minSize + Math.random() * (CONFIG.maxSize - CONFIG.minSize),
                vx: vx,
                vy: vy,
                baseVx: vx,
                baseVy: vy,
                opacity: CONFIG.minOpacity + Math.random() * (CONFIG.maxOpacity - CONFIG.minOpacity),
                pulseSpeed: 0.4 + Math.random() * 0.8,
                pulseOffset: Math.random() * Math.PI * 2,
                
                // Rotaciones iniciales y velocidades de rotación (3D)
                rx: Math.random() * Math.PI * 2,
                ry: Math.random() * Math.PI * 2,
                rz: Math.random() * Math.PI * 2,
                vrx: (Math.random() - 0.5) * 0.012,
                vry: (Math.random() - 0.5) * 0.012,
                vrz: (Math.random() - 0.5) * 0.012,
            });
        }
    }

    // ==========================================
    // ANIMACIÓN
    // ==========================================

    let elapsed = 0;

    function step() {
        elapsed += 1;
        ctx.clearRect(0, 0, width, height);

        // 1. Repulsión entre cubos para evitar solapamientos feos
        for (let i = 0; i < cubes.length; i++) {
            for (let j = i + 1; j < cubes.length; j++) {
                const c1 = cubes[i];
                const c2 = cubes[j];
                const dx = c1.x - c2.x;
                const dy = c1.y - c2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                const minDist = (c1.size + c2.size) * 1.1;

                if (dist < minDist && dist > 0) {
                    const force = (minDist - dist) / minDist;
                    const pushX = (dx / dist) * force * 0.04;
                    const pushY = (dy / dist) * force * 0.04;

                    c1.vx += pushX;
                    c1.vy += pushY;
                    c2.vx -= pushX;
                    c2.vy -= pushY;
                }
            }
        }

        // 2. Actualizar posiciones e interacciones de física
        cubes.forEach((cube) => {
            // Interacción de repulsión con el cursor del mouse
            if (mouse.active) {
                const dx = cube.x - mouse.x;
                const dy = cube.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 180) {
                    const force = (180 - dist) / 180;
                    cube.vx += (dx / dist) * force * 0.25;
                    cube.vy += (dy / dist) * force * 0.25;
                }
            }

            // Retorno gradual a la velocidad base (fricción/damping)
            cube.vx += (cube.baseVx - cube.vx) * 0.035;
            cube.vy += (cube.baseVy - cube.vy) * 0.035;

            // Limitar velocidad máxima de escape
            const maxSpeed = CONFIG.speed * 6;
            const currentSpeed = Math.sqrt(cube.vx * cube.vx + cube.vy * cube.vy);
            if (currentSpeed > maxSpeed) {
                cube.vx = (cube.vx / currentSpeed) * maxSpeed;
                cube.vy = (cube.vy / currentSpeed) * maxSpeed;
            }

            // Movimiento flotante
            cube.x += cube.vx;
            cube.y += cube.vy;

            // Rotación 3D
            cube.rx += cube.vrx;
            cube.ry += cube.vry;
            cube.rz += cube.vrz;

            // Rebote y envoltorio suave en los bordes
            const margin = cube.size;
            if (cube.x < -margin) cube.x = width + margin;
            if (cube.x > width + margin) cube.x = -margin;
            if (cube.y < -margin) cube.y = height + margin;
            if (cube.y > height + margin) cube.y = -margin;
        });

        // 3. Dibujar red de líneas de conexión entre cubos (Logística y Rutas)
        cubes.forEach((c1, i) => {
            const t1 = Math.max(0, Math.min(1, c1.y / height));
            const col1 = colorAt(t1);

            for (let j = i + 1; j < cubes.length; j++) {
                const c2 = cubes[j];
                const dx = c1.x - c2.x;
                const dy = c1.y - c2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 180) {
                    const factor = 1 - (dist / 180);
                    const pulse = 0.7 + 0.3 * Math.sin(elapsed * 0.015 + (c1.pulseOffset + c2.pulseOffset)/2);
                    const alpha = factor * 0.16 * ((c1.opacity + c2.opacity) / 2) * pulse;

                    // Color promedio entre nodos
                    const r = Math.round((col1.r + colorAt(c2.y / height).r) / 2);
                    const g = Math.round((col1.g + colorAt(c2.y / height).g) / 2);
                    const b = Math.round((col1.b + colorAt(c2.y / height).b) / 2);

                    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
                    ctx.lineWidth = 0.8;
                    ctx.beginPath();
                    ctx.moveTo(c1.x, c1.y);
                    ctx.lineTo(c2.x, c2.y);
                    ctx.stroke();
                }
            }
        });

        // 4. Dibujar líneas desde el mouse hacia los cubos más cercanos
        if (mouse.active) {
            cubes.forEach((cube) => {
                const dx = cube.x - mouse.x;
                const dy = cube.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 200) {
                    const factor = 1 - (dist / 200);
                    const { r, g, b } = colorAt(cube.y / height);
                    ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${factor * 0.22})`;
                    ctx.lineWidth = 0.7;
                    ctx.beginPath();
                    ctx.moveTo(mouse.x, mouse.y);
                    ctx.lineTo(cube.x, cube.y);
                    ctx.stroke();
                }
            });
        }

        // 5. Dibujar los Cubos 3D
        cubes.forEach((cube) => {
            // Calcular color dinámico según su altura en pantalla actual
            const t = Math.max(0, Math.min(1, cube.y / height));
            const { r, g, b } = colorAt(t);

            const pulse = 0.75 + 0.25 * Math.sin(elapsed * 0.015 * cube.pulseSpeed + cube.pulseOffset);
            const alpha = cube.opacity * pulse;

            // Proyectar todos los vértices en 3D
            const projectedVertices = VERTICES.map(vertex => {
                const rotated = rotate3D(vertex, cube.rx, cube.ry, cube.rz);
                return project(rotated, cube);
            });

            // A) Relleno de las Caras en 3D (para simular volumen translúcido)
            ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.08})`;
            FACES.forEach((face) => {
                ctx.beginPath();
                ctx.moveTo(projectedVertices[face[0]].x, projectedVertices[face[0]].y);
                for (let k = 1; k < 4; k++) {
                    ctx.lineTo(projectedVertices[face[k]].x, projectedVertices[face[k]].y);
                }
                ctx.closePath();
                ctx.fill();
            });

            // B) Dibujar Aristas (Doble trazo para simular resplandor sin lag)
            // Trazo base del brillo
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.18})`;
            ctx.lineWidth = 4.0;
            EDGES.forEach((edge) => {
                ctx.beginPath();
                ctx.moveTo(projectedVertices[edge[0]].x, projectedVertices[edge[0]].y);
                ctx.lineTo(projectedVertices[edge[1]].x, projectedVertices[edge[1]].y);
                ctx.stroke();
            });

            // Trazo central nítido
            ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${alpha * 0.65})`;
            ctx.lineWidth = 1.0;
            EDGES.forEach((edge) => {
                ctx.beginPath();
                ctx.moveTo(projectedVertices[edge[0]].x, projectedVertices[edge[0]].y);
                ctx.lineTo(projectedVertices[edge[1]].x, projectedVertices[edge[1]].y);
                ctx.stroke();
            });
        });

        animationId = requestAnimationFrame(step);
    }

    // ==========================================
    // INICIAR
    // ==========================================

    function init() {
        resize();

        if (height < 200) {
            requestAnimationFrame(init);
            return;
        }

        createCubes();
        cancelAnimationFrame(animationId);
        step();
    }

    // ==========================================
    // PAUSAR CUANDO LA PÁGINA NO ESTÁ VISIBLE
    // ==========================================

    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            cancelAnimationFrame(animationId);
        } else {
            step();
        }
    });

    // ==========================================
    // SEGUIMIENTO DE MOUSE (A nivel global)
    // ==========================================

    window.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        if (e.clientX >= rect.left && e.clientX <= rect.right &&
            e.clientY >= rect.top && e.clientY <= rect.bottom) {
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;
            mouse.active = true;
        } else {
            mouse.active = false;
        }
    });

    window.addEventListener('mouseleave', () => {
        mouse.active = false;
    });

    // ==========================================
    // REDIMENSIONAR
    // ==========================================

    function handleResize() {
        const zone = canvas.parentElement;
        if (!zone || !nodes_ready()) return;

        const rect = zone.getBoundingClientRect();
        const newWidth = Math.round(rect.width);
        const newHeight = Math.round(rect.height);

        if (newWidth === width && newHeight === height) return;

        if (!cubes || cubes.length === 0) {
            init();
            return;
        }

        const scaleX = newWidth / width;
        const scaleY = newHeight / height;

        width = canvas.width = newWidth;
        height = canvas.height = newHeight;

        cubes.forEach((cube) => {
            cube.x *= scaleX;
            cube.y *= scaleY;
        });
    }

    function nodes_ready() {
        return typeof width === 'number' && typeof height === 'number';
    }

    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(handleResize, 150);
    });

    // ==========================================
    // DESACTIVAR EN MÓVIL
    // ==========================================

    if (window.matchMedia('(max-width: 767px)').matches) {
        return;
    }

    // ==========================================
    // INICIAR ANIMACIÓN
    // ==========================================

    if (document.readyState === 'complete') {
        init();
    } else {
        window.addEventListener('load', init);
    }

})();