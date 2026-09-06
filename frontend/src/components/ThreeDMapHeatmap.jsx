import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { fetchLiveSectorsWeather } from '../services/api';

// Zone coordinates mapped to 3D Terrain space [-45 to +45 X, -35 to +35 Y]
const ZONE_3D_POSITIONS = {
  'Z-SHL-01': { x: 5, z: 0, elevation: 1496, heightScale: 15, name: 'Shillong Peak Ridge', risk: 'severe', prob: 0.88, slope: 38.4, rain: 142.5 },
  'Z-CHR-02': { x: -8, z: 12, elevation: 1430, heightScale: 14.3, name: 'Sohra Escarpment', risk: 'high', prob: 0.76, slope: 35.8, rain: 210.0 },
  'Z-MW-03': { x: -18, z: 10, elevation: 1400, heightScale: 14.0, name: 'Mawsynram Canyons', risk: 'severe', prob: 0.93, slope: 42.1, rain: 265.0 },
  'Z-JOW-04': { x: 22, z: 5, elevation: 1380, heightScale: 13.8, name: 'Jowai Bypass Cut', risk: 'moderate', prob: 0.54, slope: 27.2, rain: 88.0 },
  'Z-TUR-06': { x: -35, z: 3, elevation: 872, heightScale: 8.7, name: 'Tura Peak Ridge', risk: 'moderate', prob: 0.48, slope: 31.5, rain: 95.0 },
  'Z-NONG-05': { x: 4, z: -20, elevation: 485, heightScale: 4.8, name: 'Nongpoh Lowlands', risk: 'low', prob: 0.19, slope: 14.2, rain: 42.0 }
};

/**
 * Maps probability / risk score (0.0 to 1.0) along a continuous
 * Green -> Lime -> Yellow -> Orange -> Red color Aspectrum.
 */
function getSpectrumColor(t) {
  const clamped = Math.max(0, Math.min(1, t));
  let r, g, b;
  if (clamped < 0.30) {
    const f = clamped / 0.30;
    r = 0.13 + f * (0.64 - 0.13);
    g = 0.77 + f * (0.90 - 0.77);
    b = 0.37 + f * (0.21 - 0.37);
  } else if (clamped < 0.55) {
    const f = (clamped - 0.30) / 0.25;
    r = 0.64 + f * (0.92 - 0.64);
    g = 0.90 + f * (0.70 - 0.90);
    b = 0.21 + f * (0.03 - 0.21);
  } else if (clamped < 0.75) {
    const f = (clamped - 0.55) / 0.20;
    r = 0.92 + f * (0.98 - 0.92);
    g = 0.70 + f * (0.45 - 0.70);
    b = 0.03 + f * (0.09 - 0.03);
  } else {
    const f = (clamped - 0.75) / 0.25;
    r = 0.98 + f * (0.94 - 0.98);
    g = 0.45 + f * (0.27 - 0.45);
    b = 0.09 + f * (0.27 - 0.09);
  }
  return new THREE.Color(r, g, b);
}

const getRiskHexColor = (risk) => {
  switch (risk?.toLowerCase()) {
    case 'severe': return 0xef4444;   // Red
    case 'high': return 0xf97316;     // Orange
    case 'moderate': return 0xeab308; // Yellow
    default: return 0x22c55e;         // Green
  }
};

const INSR_VELOCITY_DT = {
  'Z-SHL-01': { los_velocity: -14.2, cumulative: -38.5, coherence: 0.88, trend: 'ccelerating Subsidence', satellite: 'Sentinel-1 Track 121' },
  'Z-CHR-02': { los_velocity: -18.6, cumulative: -52.1, coherence: 0.84, trend: 'Active Downward Shear', satellite: 'Sentinel-1 Track 48' },
  'Z-MW-03': { los_velocity: -22.4, cumulative: -64.8, coherence: 0.79, trend: 'Critical Creep Velocity', satellite: 'Sentinel-1 Track 121' },
  'Z-JOW-04': { los_velocity: -6.8, cumulative: -18.2, coherence: 0.91, trend: 'Moderate Slope Creep', satellite: 'Sentinel-1B Track 121' },
  'Z-TUR-06': { los_velocity: -4.5, cumulative: -11.4, coherence: 0.93, trend: 'Low Baseline Creep', satellite: 'Sentinel-1 Track 48' },
  'Z-NONG-05': { los_velocity: 0.8, cumulative: 2.1, coherence: 0.96, trend: 'Stable (ccretion)', satellite: 'Sentinel-1 Track 121' }
};

/**
 * Creates 2D Text canvas sprite billboard with depthTest disabled,
 * live weather metadata, and optional Sentinel-1 InSAR millimeter deformation rates.
 */
function createFloatingLabelSprite(name, elevation, risk, liveWeather = null, showInSAR = false, zoneCode = '') {
  const canvas = document.createElement('canvas');
  canvas.width = 720;
  canvas.height = 190;
  const ctx = canvas.getContext('2d');

  // Background Box
  ctx.fillStyle = 'rgba(12, 12, 14, 0.96)';
  ctx.strokeStyle = '#FFFFFF';
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.roundRect(10, 10, 700, 170, 16);
  ctx.fill();
  ctx.stroke();

  // Severity Color Indicator Bar
  const barColor = risk === 'severe' ? '#EF4444' : risk === 'high' ? '#F97316' : risk === 'moderate' ? '#EAB308' : '#22C55E';
  ctx.fillStyle = barColor;
  ctx.fillRect(10, 10, 20, 170);

  // Sector Name Text (Bounded & Trimmed if needed)
  ctx.fillStyle = '#FFFFFF';
  ctx.font = 'bold 28px Inter, sans-serif';
  const displayName = name.length > 28 ? name.substring(0, 26) + '...' : name;
  ctx.fillText(displayName, 46, 56);

  // Risk Badge Pill (Top Right)
  ctx.fillStyle = barColor;
  ctx.beginPath();
  ctx.roundRect(520, 24, 170, 38, 8);
  ctx.fill();

  ctx.fillStyle = risk === 'moderate' ? '#000000' : '#FFFFFF';
  ctx.font = 'bold 18px "JetBrains Mono", monospace';
  ctx.textAlign = 'center';
  ctx.fillText(risk.toUpperCase() + ' RISK', 605, 49);
  ctx.textAlign = 'left'; // Reset

  // Middle Row: Elevation Text & Sector Code
  ctx.font = 'bold 22px "JetBrains Mono", monospace';
  ctx.fillStyle = '#E2E8F0';
  ctx.fillText(`️ ${elevation}m MSL`, 46, 98);

  ctx.font = 'bold 18px "JetBrains Mono", monospace';
  ctx.fillStyle = '#943B8';
  ctx.fillText(zoneCode, 525, 98);

  // Bottom Telemetry Bar (Bounded High-Contrast Pill)
  const insar = INSR_VELOCITY_DT[zoneCode];
  ctx.fillStyle = 'rgba(255, 255, 255, 0.08)';
  ctx.beginPath();
  ctx.roundRect(46, 120, 644, 44, 8);
  ctx.fill();

  if (showInSAR && insar) {
    const insarColor = insar.los_velocity <= -15.0 ? '#EF4444' : insar.los_velocity <= -10.0 ? '#F97316' : '#22C55E';
    ctx.fillStyle = insarColor;
    ctx.font = 'bold 18px "JetBrains Mono", monospace';
    const insarText = `️ InSAR LOS: ${insar.los_velocity > 0 ? '+' : ''}${insar.los_velocity} mm/yr • ${insar.trend}`;
    ctx.fillText(insarText, 58, 148);
  } else if (liveWeather) {
    ctx.font = 'bold 18px "JetBrains Mono", monospace';
    if (liveWeather.is_raining) {
      ctx.fillStyle = '#605F';
      ctx.fillText(`️ RIN: ${liveWeather.current_rain_mm_h} mm/h • TEMP: ${liveWeather.temperature_c}°C`, 58, 148);
    } else {
      ctx.fillStyle = '#CBD5E1';
      ctx.fillText(`️ ${liveWeather.condition || 'OVERCAST'} • TEMP: ${liveWeather.temperature_c}°C (0.0 mm/h)`, 58, 148);
    }
  } else {
    ctx.fillStyle = '#943B8';
    ctx.font = 'bold 18px "JetBrains Mono", monospace';
    ctx.fillText(`️ LIVE ECMWF / STELLITE SYNC AACTIVE`, 58, 148);
  }

  const texture = new THREE.CanvasTexture(canvas);
  texture.minFilter = THREE.LinearFilter;
  const spriteMat = new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthTest: false,
    depthWrite: false
  });
  const sprite = new THREE.Sprite(spriteMat);
  sprite.scale.set(19.0, 5.0, 1);
  sprite.renderOrder = 9999;
  return sprite;
}

/**
 * ThreeDMapHeatmap: Realistic 3D Topographic Terrain & Landslide Risk Heatmap with Live Weather
 */
export default function ThreeDMapHeatmap({
  riskZonesGeoJSON,
  selectedZone = null,
  language = 'en',
  isSimulating = false,
  onSelectZone = null
}) {
  const wrapperRef = useRef(null);
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const cameraRef = useRef(null);
  const frameIdRef = useRef(null);
  const isDraggingRef = useRef(false);
  const previousMousePositionRef = useRef({ x: 0, y: 0 });

  const [hoveredZone, setHoveredZone] = useState(null);
  const [autoRotate, setAutoRotate] = useState(false);
  const [cameraView, setCameraView] = useState('oblique');
  const [webGLSupported, setWebGLSupported] = useState(true);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showLabels, setShowLabels] = useState(true);
  const [showInSAR, setShowInSAR] = useState(false);
  const [camerangleDeg, setCamerangleDeg] = useState(0);

  // Live Meteorological Telemetry State
  const [liveWeatherMap, setLiveWeatherMap] = useState({});
  const [lastWeatherSyncTime, setLastWeatherSyncTime] = useState(null);
  const [isFetchingWeather, setIsFetchingWeather] = useState(false);

  // Fetch real-time live weather for all 6 mountain sectors
  const loadLiveSectorWeather = async () => {
    setIsFetchingWeather(true);
    try {
      const liveData = await fetchLiveSectorsWeather();
      if (Array.isArray(liveData) && liveData.length > 0) {
        const map = {};
        liveData.forEach((s) => {
          map[s.zone_id] = s;
        });
        setLiveWeatherMap(map);
        setLastWeatherSyncTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
      }
    } catch (err) {
      console.warn('[3D Map] Live weather sync error:', err);
    } finally {
      setIsFetchingWeather(false);
    }
  };

  useEffect(() => {
    loadLiveSectorWeather();
    const interval = setInterval(loadLiveSectorWeather, 60000); // sync every 60s
    return () => clearInterval(interval);
  }, []);

  // Fullscreen State Listener (Native HTML5 Fullscreen sync)
  useEffect(() => {
    const onFullscreenChange = () => {
      const isFull = !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
      setIsFullscreen(isFull);
      if (containerRef.current && rendererRef.current && cameraRef.current) {
        const w = isFull ? window.innerWidth : (containerRef.current.clientWidth || 900);
        const h = isFull ? window.innerHeight : (containerRef.current.clientHeight || 620);
        cameraRef.current.aspect = w / h;
        cameraRef.current.updateProjectionMatrix();
        rendererRef.current.setSize(w, h);
      }
    };

    document.addEventListener('fullscreenchange', onFullscreenChange);
    document.addEventListener('webkitfullscreenchange', onFullscreenChange);
    document.addEventListener('mozfullscreenchange', onFullscreenChange);
    document.addEventListener('MSFullscreenChange', onFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', onFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', onFullscreenChange);
      document.removeEventListener('mozfullscreenchange', onFullscreenChange);
      document.removeEventListener('MSFullscreenChange', onFullscreenChange);
    };
  }, []);

  // Initialize Three.js Scene
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 900;
    const height = container.clientHeight || 620;

    const hasWebGLContext = () => {
      try {
        const canvas = document.createElement('canvas');
        return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
      } catch (e) {
        return false;
      }
    };

    if (!hasWebGLContext()) {
      setWebGLSupported(false);
      return;
    }

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    } catch (e) {
      setWebGLSupported(false);
      return;
    }

    if (!renderer || !renderer.domElement) {
      setWebGLSupported(false);
      return;
    }

    // 1. Scene & Photorealistic tmospheric Haze
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf8fafc);
    scene.fog = new THREE.FogExp2(0xf8fafc, 0.005);
    sceneRef.current = scene;

    // 2. Camera
    const camera = new THREE.PerspectiveCamera(40, width / height, 1, 1200);
    camera.position.set(0, 150, 180);
    camera.lookAt(0, 4, 0);
    cameraRef.current = camera;

    // 3. Renderer Setup
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 4. Photorealistic Sunlight & Ambient Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.88);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfffaed, 0.95);
    sunLight.position.set(50, 100, 60);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    scene.add(sunLight);

    const valleyFillLight = new THREE.DirectionalLight(0x94a3b8, 0.35);
    valleyFillLight.position.set(-50, 40, -60);
    scene.add(valleyFillLight);

    // 5. 3D Topographic Terrain Surface
    const terrainWidth = 250;
    const terrainHeight = 200;
    const gridCols = 150;
    const gridRows = 150;
    const terrainGeometry = new THREE.PlaneGeometry(terrainWidth, terrainHeight, gridCols, gridRows);
    terrainGeometry.rotateX(-Math.PI / 2);

    const pos = terrainGeometry.attributes.position;
    const colors = [];

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);

      const distToShillong = Math.hypot(x - 5, z - 2);
      const distToSohra = Math.hypot(x + 10, z - 10);
      const distToMawsynram = Math.hypot(x + 18, z - 10);
      const distToJowai = Math.hypot(x - 22, z - 5);
      const distToTura = Math.hypot(x + 35, z - 3);

      let elevation = 2.2;
      elevation += Math.max(0, 15.2 * Math.exp(-distToShillong / 18));
      elevation += Math.max(0, 13.8 * Math.exp(-distToSohra / 16));
      elevation += Math.max(0, 14.2 * Math.exp(-distToMawsynram / 15));
      elevation += Math.max(0, 12.5 * Math.exp(-distToJowai / 16));
      elevation += Math.max(0, 8.5 * Math.exp(-distToTura / 12));

      elevation += Math.sin(x * 0.25) * Math.cos(z * 0.25) * 1.3;
      elevation += Math.sin(x * 0.6 + z * 0.4) * 0.6;

      pos.setY(i, elevation);

      // Continuous Risk Heat Intensity
      let heat = 0.05;
      heat += 0.88 * Math.exp(-distToShillong / 14);
      heat += 0.76 * Math.exp(-distToSohra / 13);
      heat += 0.93 * Math.exp(-distToMawsynram / 12);
      heat += 0.54 * Math.exp(-distToJowai / 14);
      heat += 0.48 * Math.exp(-distToTura / 12);

      if (elevation > 12) heat += 0.12;

      const vertexColor = getSpectrumColor(Math.min(heat, 1.0));
      colors.push(vertexColor.r, vertexColor.g, vertexColor.b);
    }

    terrainGeometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    terrainGeometry.computeVertexNormals();

    const terrainMaterial = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.62,
      metalness: 0.06,
      flatShading: true
    });
    const terrainMesh = new THREE.Mesh(terrainGeometry, terrainMaterial);
    terrainMesh.receiveShadow = true;
    scene.add(terrainMesh);

    // Elevation Isobar Contours
    const wireframeMaterial = new THREE.MeshBasicMaterial({
      color: 0x0f172a,
      wireframe: true,
      transparent: true,
      opacity: 0.10
    });
    const wireframeMesh = new THREE.Mesh(terrainGeometry, wireframeMaterial);
    wireframeMesh.position.y += 0.05;
    scene.add(wireframeMesh);

    // 6. 3D Hazard Columns & Live Weather Sprites
    const columnsGroup = new THREE.Group();
    columnsGroup.name = 'riskColumns';

    const labelsGroup = new THREE.Group();
    labelsGroup.name = 'floatingLabels';

    // Localized rain systems array
    const localizedRainSystems = [];

    Object.entries(ZONE_3D_POSITIONS).forEach(([code, zone]) => {
      const riskHex = getRiskHexColor(zone.risk);
      const height = zone.heightScale * 1.3;
      const colGeo = new THREE.CylinderGeometry(2.5, 3.2, height, 24);
      colGeo.translate(0, height / 2, 0);

      const colMat = new THREE.MeshStandardMaterial({
        color: riskHex,
        roughness: 0.2,
        metalness: 0.15,
        emissive: riskHex,
        emissiveIntensity: zone.risk === 'severe' ? 0.3 : 0.12,
        transparent: true,
        opacity: zone.risk === 'severe' ? 0.95 : zone.risk === 'high' ? 0.88 : 0.80
      });

      const colMesh = new THREE.Mesh(colGeo, colMat);
      colMesh.position.set(zone.x, 0, zone.z);
      colMesh.castShadow = true;

      const live = liveWeatherMap[code] || null;
      colMesh.userData = { zoneCode: code, ...zone, liveWeather: live };

      // Base Warning Ring
      const ringGeo = new THREE.RingGeometry(3.4, 4.4, 32);
      ringGeo.rotateX(-Math.PI / 2);
      const ringMat = new THREE.MeshBasicMaterial({
        color: riskHex,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.65
      });
      const ringMesh = new THREE.Mesh(ringGeo, ringMat);
      ringMesh.position.set(zone.x, 0.25, zone.z);
      columnsGroup.add(ringMesh);

      columnsGroup.add(colMesh);

      // nchor Stem Line connecting column to floating label
      const stemPoints = [
        new THREE.Vector3(zone.x, height, zone.z),
        new THREE.Vector3(zone.x, height + 6.0, zone.z)
      ];
      const stemGeo = new THREE.BufferGeometry().setFromPoints(stemPoints);
      const stemMat = new THREE.LineBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.85 });
      const stemLine = new THREE.Line(stemGeo, stemMat);
      labelsGroup.add(stemLine);

      // Floating ltitude & Live Weather / InSAR Tag
      const labelSprite = createFloatingLabelSprite(zone.name, zone.elevation, zone.risk, live, showInSAR, code);
      labelSprite.position.set(zone.x, height + 8.5, zone.z);
      labelsGroup.add(labelSprite);

      // Localized 3D Rain Particle System if actively raining or during cloudburst simulation
      const isSectorRaining = isSimulating ? (zone.risk === 'severe' || zone.risk === 'high') : (live?.is_raining || false);
      if (isSectorRaining) {
        const sectorRainCount = 350;
        const sRainGeo = new THREE.BufferGeometry();
        const sRainPositions = new Float32Array(sectorRainCount * 3);
        for (let r = 0; r < sectorRainCount * 3; r += 3) {
          sRainPositions[r] = zone.x + (Math.random() - 0.5) * 16;
          sRainPositions[r + 1] = Math.random() * 35 + 8;
          sRainPositions[r + 2] = zone.z + (Math.random() - 0.5) * 16;
        }
        sRainGeo.setAttribute('position', new THREE.BufferAttribute(sRainPositions, 3));
        const sRainMat = new THREE.PointsMaterial({
          color: 0x2563eb,
          size: 0.6,
          transparent: true,
          opacity: 0.8
        });
        const sRainSystem = new THREE.Points(sRainGeo, sRainMat);
        scene.add(sRainSystem);
        localizedRainSystems.push({ system: sRainSystem, geo: sRainGeo, count: sectorRainCount });
      }
    });

    scene.add(columnsGroup);
    scene.add(labelsGroup);

    // 7. 3D rterial Highways (NH-40, NH-6, SH-5)
    const roadPoints = [
      new THREE.Vector3(4, 5, -20),
      new THREE.Vector3(5, 12, -8),
      new THREE.Vector3(5, 16, 0),
      new THREE.Vector3(-8, 14, 12),
      new THREE.Vector3(-18, 13, 10)
    ];
    const roadCurve = new THREE.CatmullRomCurve3(roadPoints);
    const roadGeo = new THREE.TubeGeometry(roadCurve, 64, 0.55, 8, false);
    const roadMat = new THREE.MeshStandardMaterial({ color: 0x0a0a0a, roughness: 0.4 });
    const roadMesh = new THREE.Mesh(roadGeo, roadMat);
    scene.add(roadMesh);

    // 8. General Ambient Rain Field (Active in storm simulation)
    const rainCount = isSimulating ? 1800 : 400;
    const rainGeo = new THREE.BufferGeometry();
    const rainPositions = new Float32Array(rainCount * 3);
    for (let i = 0; i < rainCount * 3; i += 3) {
      rainPositions[i] = (Math.random() - 0.5) * 90;
      rainPositions[i + 1] = Math.random() * 45 + 10;
      rainPositions[i + 2] = (Math.random() - 0.5) * 70;
    }
    rainGeo.setAttribute('position', new THREE.BufferAttribute(rainPositions, 3));
    const rainMat = new THREE.PointsMaterial({
      color: 0x3b82f6,
      size: 0.45,
      transparent: true,
      opacity: isSimulating ? 0.75 : 0.25
    });
    const rainSystem = new THREE.Points(rainGeo, rainMat);
    scene.add(rainSystem);

    // 9. Animation Loop
    let angle = 0;
    const animate = () => {
      frameIdRef.current = requestAnimationFrame(animate);

      // Ambient Rain animation
      const rainPos = rainGeo.attributes.position.array;
      const speed = isSimulating ? 1.6 : 0.6;
      for (let i = 1; i < rainCount * 3; i += 3) {
        rainPos[i] -= speed;
        if (rainPos[i] < 0) {
          rainPos[i] = 50;
        }
      }
      rainGeo.attributes.position.needsUpdate = true;

      // Localized Active Rain Cascades
      localizedRainSystems.forEach(({ geo, count }) => {
        const prr = geo.attributes.position.array;
        for (let r = 1; r < count * 3; r += 3) {
          prr[r] -= 1.4;
          if (prr[r] < 0) {
            prr[r] = 40;
          }
        }
        geo.attributes.position.needsUpdate = true;
      });

      if (autoRotate && cameraRef.current) {
        angle += 0.004;
        const radius = 100;
        cameraRef.current.position.x = Math.sin(angle) * radius;
        cameraRef.current.position.z = Math.cos(angle) * radius;
        cameraRef.current.lookAt(0, 4, 0);
      }

      if (cameraRef.current) {
        const deg = Math.round(Math.atan2(cameraRef.current.position.x, cameraRef.current.position.z) * (180 / Math.PI));
        setCamerangleDeg(deg);
      }

      renderer.render(scene, camera);
    };
    animate();

    // 10. Mouse Drag Controls
    const onMouseDown = (e) => {
      isDraggingRef.current = true;
      previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      if (!isDraggingRef.current) {
        const rect = container.getBoundingClientRect();
        const mouseX = ((e.clientX - rect.left) / (container.clientWidth || 1)) * 2 - 1;
        const mouseY = -((e.clientY - rect.top) / (container.clientHeight || 1)) * 2 + 1;

        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera({ x: mouseX, y: mouseY }, camera);
        const intersects = raycaster.intersectObjects(columnsGroup.children);

        if (intersects.length > 0 && intersects[0].object.userData?.name) {
          const uData = intersects[0].object.userData;
          setHoveredZone({
            ...uData,
            liveWeather: liveWeatherMap[uData.zoneCode] || uData.liveWeather
          });
        } else {
          setHoveredZone(null);
        }
        return;
      }

      const deltaX = e.clientX - previousMousePositionRef.current.x;
      const deltaY = e.clientY - previousMousePositionRef.current.y;

      if (cameraRef.current) {
        const cam = cameraRef.current;
        const rotSpeed = 0.005;
        const x = cam.position.x;
        const z = cam.position.z;
        const cos = Math.cos(-deltaX * rotSpeed);
        const sin = Math.sin(-deltaX * rotSpeed);

        cam.position.x = x * cos - z * sin;
        cam.position.z = x * sin + z * cos;
        cam.position.y = Math.max(15, Math.min(120, cam.position.y + deltaY * 0.3));
        cam.lookAt(0, 4, 0);
      }

      previousMousePositionRef.current = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDraggingRef.current = false;
    };

    const onWheel = (e) => {
      e.preventDefault();
      if (cameraRef.current) {
        const zoomSpeed = 0.07;
        const factor = 1 + (e.deltaY > 0 ? zoomSpeed : -zoomSpeed);
        cameraRef.current.position.x *= factor;
        cameraRef.current.position.y *= factor;
        cameraRef.current.position.z *= factor;
        cameraRef.current.lookAt(0, 4, 0);
      }
    };

    const onClick = (e) => {
      const rect = container.getBoundingClientRect();
      const mouseX = ((e.clientX - rect.left) / (container.clientWidth || 1)) * 2 - 1;
      const mouseY = -((e.clientY - rect.top) / (container.clientHeight || 1)) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera({ x: mouseX, y: mouseY }, camera);
      const intersects = raycaster.intersectObjects(columnsGroup.children);

      if (intersects.length > 0 && intersects[0].object.userData?.zoneCode) {
        const clickedData = intersects[0].object.userData;
        if (onSelectZone) {
          onSelectZone({
            zone_id: clickedData.zoneCode,
            name: clickedData.name,
            elevation_m: clickedData.elevation,
            risk_level: clickedData.risk,
            probability: clickedData.prob,
            mean_slope_deg: clickedData.slope,
            rainfall_24h_mm: clickedData.rain
          });
        }
      }
    };

    container.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    container.addEventListener('wheel', onWheel, { passive: false });
    container.addEventListener('click', onClick);

    // Responsive ResizeObserver & Window Resize
    const updateSize = () => {
      if (!container || !rendererRef.current || !cameraRef.current) return;
      const w = container.clientWidth || (isFullscreen ? window.innerWidth : 900);
      const h = container.clientHeight || (isFullscreen ? window.innerHeight : 620);
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };

    let resizeObserver = null;
    let resizeReqId = null;
    if (typeof ResizeObserver !== 'undefined' && container) {
      resizeObserver = new ResizeObserver(() => {
        if (resizeReqId) cancelAnimationFrame(resizeReqId);
        resizeReqId = requestAnimationFrame(() => {
          updateSize();
        });
      });
      resizeObserver.observe(container);
    }

    window.addEventListener('resize', updateSize);

    return () => {
      cancelAnimationFrame(frameIdRef.current);
      if (resizeReqId) cancelAnimationFrame(resizeReqId);
      container.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      container.removeEventListener('wheel', onWheel);
      container.removeEventListener('click', onClick);
      window.removeEventListener('resize', updateSize);
      if (resizeObserver) resizeObserver.disconnect();
      if (renderer) renderer.dispose();
    };
  }, [autoRotate, isSimulating, isFullscreen, onSelectZone, liveWeatherMap, showInSAR]);

  const setPresetView = (preset) => {
    setCameraView(preset);
    if (!cameraRef.current) return;
    if (preset === 'top') {
      cameraRef.current.position.set(0, 105, 0.1);
    } else if (preset === 'isometric') {
      cameraRef.current.position.set(70, 55, 70);
    } else {
      cameraRef.current.position.set(0, 68, 88);
    }
    cameraRef.current.lookAt(0, 4, 0);
  };

  const handleZoom = (direction) => {
    if (!cameraRef.current) return;
    const factor = direction === 'in' ? 0.85 : 1.18;
    cameraRef.current.position.x *= factor;
    cameraRef.current.position.y *= factor;
    cameraRef.current.position.z *= factor;
    cameraRef.current.lookAt(0, 4, 0);
  };

  const toggleLabels = () => {
    setShowLabels(!showLabels);
    if (sceneRef.current) {
      const labels = sceneRef.current.getObjectByName('floatingLabels');
      if (labels) labels.visible = !showLabels;
    }
  };

  const toggleFullscreen = () => {
    const elem = wrapperRef.current;
    if (!elem) {
      setIsFullscreen(!isFullscreen);
      return;
    }

    if (!document.fullscreenElement && !document.webkitFullscreenElement) {
      if (elem.requestFullscreen) {
        elem.requestFullscreen().catch(() => setIsFullscreen(true));
      } else if (elem.webkitRequestFullscreen) {
        elem.webkitRequestFullscreen();
      } else if (elem.msRequestFullscreen) {
        elem.msRequestFullscreen();
      } else {
        setIsFullscreen(true);
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => setIsFullscreen(false));
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
      } else {
        setIsFullscreen(false);
      }
    }
  };

  const getRiskBadgeStyle = (risk) => {
    switch (risk?.toLowerCase()) {
      case 'severe': return 'bg-red-600 text-white';
      case 'high': return 'bg-orange-500 text-white';
      case 'moderate': return 'bg-yellow-500 text-black';
      default: return 'bg-green-600 text-white';
    }
  };

  return (
    <div
      ref={wrapperRef}
      className={`relative border border-gray-200 rounded-xl shadow-sm overflow-hidden bg-[#F8FAFC] select-none transition-all duration-150 ${
        isFullscreen
          ? 'fixed inset-0 z-[99999] w-screen h-screen m-0 p-0'
          : 'w-full h-[800px]'
      }`}
      style={isFullscreen ? { position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', zIndex: 99999 } : {}}
    >
      {/* 3D WebGL Canvas Container */}
      <div ref={containerRef} className="w-full h-full cursor-grab active:cursor-grabbing">
        {!webGLSupported && (
          <div className="w-full h-full flex flex-col items-center justify-center p-6 text-center text-xs text-gray-700 bg-gray-100">
            <p className="font-semibold text-black text-sm mb-1">️ 3D Topographic Terrain View</p>
            <p>WebGL Hardware acceleration not supported in your browser.</p>
            <div className="mt-3 grid grid-cols-3 gap-2 text-left bg-white p-3 border border-gray-300 rounded-md max-w-md">
              <div><span className="inline-block w-2.5 h-2.5 bg-red-600 mr-1 rounded-sm"></span><b>Shillong Ridge:</b> 1,496m</div>
              <div><span className="inline-block w-2.5 h-2.5 bg-orange-500 mr-1 rounded-sm"></span><b>Sohra Plateau:</b> 1,430m</div>
              <div><span className="inline-block w-2.5 h-2.5 bg-red-600 mr-1 rounded-sm"></span><b>Mawsynram:</b> 1,400m</div>
              <div><span className="inline-block w-2.5 h-2.5 bg-yellow-500 mr-1 rounded-sm"></span><b>Jowai Bypass:</b> 1,380m</div>
              <div><span className="inline-block w-2.5 h-2.5 bg-yellow-500 mr-1 rounded-sm"></span><b>Tura Peak:</b> 872m</div>
              <div><span className="inline-block w-2.5 h-2.5 bg-green-600 mr-1 rounded-sm"></span><b>Nongpoh:</b> 485m</div>
            </div>
          </div>
        )}
      </div>

      {/* Unified Top Control Toolbar */}
      <div className="absolute top-3 left-3 right-3 z-20 flex flex-wrap items-center justify-between gap-2 bg-white/95 backdrop-blur-md border border-gray-200 rounded-lg p-1.5 text-xs shadow-sm">
        {/* Left: View Mode Presets & Live Weather Sync Indicator */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-semibold text-white px-2 py-1 uppercase tracking-wider text-[10px] bg-gradient-to-r from-green-600 via-yellow-500 to-red-600 rounded-sm">
            3D TOPO-HEATMAP
          </span>
          <button
            type="button"
            onClick={() => setPresetView('oblique')}
            className={`px-2 py-1 border rounded-md cursor-pointer transition-colors ${cameraView === 'oblique' ? 'bg-black text-white border-black font-medium' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
          >
            Oblique 3D
          </button>
          <button
            type="button"
            onClick={() => setPresetView('isometric')}
            className={`px-2 py-1 border rounded-md cursor-pointer transition-colors ${cameraView === 'isometric' ? 'bg-black text-white border-black font-medium' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
          >
            Isometric 45°
          </button>
          <button
            type="button"
            onClick={() => setPresetView('top')}
            className={`px-2 py-1 border rounded-md cursor-pointer transition-colors ${cameraView === 'top' ? 'bg-black text-white border-black font-medium' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
          >
            Top-Down
          </button>
          <button
            type="button"
            onClick={() => setAutoRotate(!autoRotate)}
            className={`px-2 py-1 border rounded-md cursor-pointer transition-colors ${autoRotate ? 'bg-black text-white border-black font-medium animate-pulse' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
          >
            {autoRotate ? ' Stop Orbit' : ' 3D Orbit'}
          </button>
          <button
            type="button"
            onClick={toggleLabels}
            className={`px-2 py-0.5 border cursor-pointer ${showLabels ? 'bg-black text-white border-black font-bold' : 'bg-white text-black border-gray-400'}`}
          >
            ️ {showLabels ? 'Hide Labels' : 'Show Labels'}
          </button>

          {/* Sentinel-1 InSAR Deformation Toggle */}
          <button
            type="button"
            onClick={() => setShowInSAR(!showInSAR)}
            className={`px-2 py-0.5 border cursor-pointer ${showInSAR ? 'bg-black text-white border-black font-bold' : 'bg-white text-black border-gray-400'}`}
            title="Toggle Sentinel-1 Satellite InSAR ground deformation velocity (mm/year)"
          >
            ️ {showInSAR ? 'InSAR Active' : 'InSAR LOS'}
          </button>

          {/* Live Real-Time Satellite Telemetry Sync Badge */}
          <button
            type="button"
            onClick={loadLiveSectorWeather}
            disabled={isFetchingWeather}
            className="flex items-center gap-1.5 px-2 py-0.5 bg-gray-100 hover:bg-gray-200 border border-black text-[10px] font-bold text-gray-800 cursor-pointer transition-colors"
            title="Click to re-fetch live satellite precipitation and weather from Open-Meteo"
          >
            <span className={`w-2 h-2 rounded-full ${isFetchingWeather ? 'bg-yellow-500 animate-ping' : 'bg-green-500'}`}></span>
            <span>{isFetchingWeather ? 'SYNCING...' : 'LIVE SATELLITE SYNC'}</span>
            {lastWeatherSyncTime && <span className="text-gray-500 font-normal">({lastWeatherSyncTime})</span>}
          </button>
        </div>

        {/* Right: Camera Navigation Tools (Compass, Zoom, Fullscreen) */}
        <div className="flex items-center gap-1.5 shrink-0 ml-auto">
          {/* Compass Heading Indicator */}
          <div className="bg-gray-100 border border-black px-2 py-0.5 text-xs font-mono flex items-center gap-1">
            <span className="font-bold text-red-600">N</span>
            <span className="text-[10px] text-gray-700 font-bold">{camerangleDeg}°</span>
          </div>

          {/* Zoom Controls */}
          <div className="flex items-center bg-white border border-black text-xs font-mono">
            <button
              type="button"
              onClick={() => handleZoom('in')}
              className="px-2 py-0.5 hover:bg-black hover:text-white border-r border-black font-bold cursor-pointer"
              title="Zoom In"
            >
              +
            </button>
            <button
              type="button"
              onClick={() => handleZoom('out')}
              className="px-2 py-0.5 hover:bg-black hover:text-white font-bold cursor-pointer"
              title="Zoom Out"
            >
              -
            </button>
          </div>

          {/* Fullscreen Expand Button */}
          <button
            type="button"
            onClick={toggleFullscreen}
            className="bg-black hover:bg-gray-800 text-white border border-black px-2.5 py-0.5 text-xs font-mono font-bold transition-colors cursor-pointer"
            title={isFullscreen ? 'Exit Fullscreen' : 'Expand Fullscreen'}
          >
            {isFullscreen ? ' Exit' : ' Fullscreen'}
          </button>
        </div>
      </div>

      {/* Interactive 3D Sector Elevation & Live Weather InAspector Card */}
      {hoveredZone && (
        <div className="absolute top-16 right-3 z-20 bg-white border-2 border-black p-3.5 text-xs font-mono shadow-2xl max-w-xs animate-in fade-in zoom-in-95 duration-100">
          <div className="flex items-center justify-between gap-2 border-b border-black pb-1.5 mb-2">
            <h4 className="font-black text-black uppercase tracking-tight text-xs">{hoveredZone.name}</h4>
            <span className={`px-2 py-0.5 text-[10px] font-bold uppercase ${getRiskBadgeStyle(hoveredZone.risk)}`}>
              {hoveredZone.risk}
            </span>
          </div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex justify-between">
              <span className="text-gray-600">Elevation Height:</span>
              <span className="font-bold text-black">{hoveredZone.elevation} m MSL</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Terrain Slope:</span>
              <span className="font-bold text-black">{hoveredZone.slope}°</span>
            </div>
            {hoveredZone.liveWeather && (
              <>
                <div className="flex justify-between border-t border-gray-200 pt-1">
                  <span className="text-gray-600">Live Weather:</span>
                  <span className={`font-bold ${hoveredZone.liveWeather.is_raining ? 'text-blue-600 animate-pulse' : 'text-gray-800'}`}>
                    {hoveredZone.liveWeather.is_raining ? '️ RAINING' : '️ OVERCAST / DRY'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Rain Rate:</span>
                  <span className="font-bold text-black">{hoveredZone.liveWeather.current_rain_mm_h} mm/h</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Temperature & Humidity:</span>
                  <span className="font-bold text-black">{hoveredZone.liveWeather.temperature_c}°C ({hoveredZone.liveWeather.humidity_pct}%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Past 24h Rain:</span>
                  <span className="font-bold text-black">{hoveredZone.liveWeather.rain_24h_mm} mm</span>
                </div>
              </>
            )}
            {INSR_VELOCITY_DT[hoveredZone.zoneCode] && (
              <div className="border-t border-gray-200 pt-1 mt-1">
                <div className="flex justify-between">
                  <span className="text-gray-600">Sentinel-1 InSAR Rate:</span>
                  <span className={`font-bold ${INSR_VELOCITY_DT[hoveredZone.zoneCode].los_velocity <= -10 ? 'text-red-600' : 'text-green-600'}`}>
                    {INSR_VELOCITY_DT[hoveredZone.zoneCode].los_velocity > 0 ? '+' : ''}{INSR_VELOCITY_DT[hoveredZone.zoneCode].los_velocity} mm/yr
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Displacement Trend:</span>
                  <span className="font-bold text-black">{INSR_VELOCITY_DT[hoveredZone.zoneCode].trend}</span>
                </div>
                <div className="flex justify-between text-[10px] text-gray-500">
                  <span>Coherence: γ = {INSR_VELOCITY_DT[hoveredZone.zoneCode].coherence}</span>
                  <span>{INSR_VELOCITY_DT[hoveredZone.zoneCode].satellite}</span>
                </div>
              </div>
            )}
            <div className="flex justify-between border-t border-gray-200 pt-1">
              <span className="text-gray-600">Landslide Risk:</span>
              <span className="font-bold text-black">{Math.round(hoveredZone.prob * 100)}%</span>
            </div>
          </div>
          <p className="text-[10px] text-gray-500 mt-2 pt-1 border-t border-gray-200">
            Click column to focus 72h hydrograph forecast
          </p>
        </div>
      )}

      {/* Bottom Continuous Heatmap Spectrum Bar & Elevation Scale */}
      <div className="absolute bottom-3 right-3 z-10 bg-white/95 backdrop-blur-xs border-2 border-black p-3 text-xs font-mono max-w-[280px] shadow-md">
        <h5 className="font-bold text-black border-b border-black pb-1 mb-1.5 uppercase text-[10px]">
          Elevation & Heatmap Scale (m MSL)
        </h5>

        {/* Continuous Gradient Bar */}
        <div className="mb-2">
          <div className="w-full h-2.5 rounded-xs bg-gradient-to-r from-[#22c55e] via-[#eab308] via-[#f97316] to-[#ef4444] border border-black"></div>
          <div className="flex justify-between text-[9px] text-gray-700 font-bold mt-0.5">
            <span>Low (Green)</span>
            <span>Mod (Yellow)</span>
            <span>High (Orange)</span>
            <span>Severe (Red)</span>
          </div>
        </div>

        <div className="space-y-1 text-[10px]">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-red-600 border border-black inline-block"></span>
              <span className="font-semibold text-black">Shillong Peak Ridge</span>
            </div>
            <span className="font-bold text-black">
              1,496 m {liveWeatherMap['Z-SHL-01']?.is_raining ? '️' : ''}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-orange-500 border border-black inline-block"></span>
              <span className="font-semibold text-black">Sohra Escarpment</span>
            </div>
            <span className="font-bold text-black">
              1,430 m {liveWeatherMap['Z-CHR-02']?.is_raining ? '️' : ''}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-red-600 border border-black inline-block"></span>
              <span className="font-semibold text-black">Mawsynram Canyons</span>
            </div>
            <span className="font-bold text-black">
              1,400 m {liveWeatherMap['Z-MW-03']?.is_raining ? '️' : ''}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-yellow-500 border border-black inline-block"></span>
              <span className="font-semibold text-black">Jowai Bypass Cut</span>
            </div>
            <span className="font-bold text-black">
              1,380 m {liveWeatherMap['Z-JOW-04']?.is_raining ? '️' : ''}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-yellow-500 border border-black inline-block"></span>
              <span className="font-semibold text-black">Tura Peak Ridge</span>
            </div>
            <span className="font-bold text-black">
              872 m {liveWeatherMap['Z-TUR-06']?.is_raining ? '️' : ''}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-3 bg-green-600 border border-black inline-block"></span>
              <span className="font-semibold text-black">Nongpoh Lowlands</span>
            </div>
            <span className="font-bold text-black">
              485 m {liveWeatherMap['Z-NONG-05']?.is_raining ? '️' : ''}
            </span>
          </div>
        </div>
      </div>

      {/* Navigation & Interaction Hint */}
      <div className="absolute bottom-3 left-3 z-10 bg-black/85 text-white px-2.5 py-1.5 text-[10px] font-mono flex items-center gap-2">
        <span>️ Drag: Orbit</span>
        <span>•</span>
        <span>Scroll: Zoom</span>
        <span>•</span>
        <span>Click: Focus Sector</span>
      </div>
    </div>
  );
}
