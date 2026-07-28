import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";
import { retargetAnimation } from "vrm-mixamo-retarget";

// ========================
// AUDIO STREAMING & LIP SYNC
// ========================

const audioContext = new AudioContext({
  sampleRate: 24000,
});

let nextAudioTime = 0;

// Create an Analyser Node for real-time lip sync
const analyser = audioContext.createAnalyser();
analyser.fftSize = 256;
analyser.connect(audioContext.destination);

let currentMouthValue = 0;
let targetMouthValue = 0;

// ========================
// THREE.JS SETUP
// ========================

// renderer
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.body.appendChild(renderer.domElement);

// camera
const camera = new THREE.PerspectiveCamera(
  30.0,
  window.innerWidth / window.innerHeight,
  0.1,
  20.0,
);

camera.position.set(0.0, 1.0, 5.0);

// camera controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.screenSpacePanning = true;
controls.target.set(0.0, 1.0, 0.0);
controls.update();

// scene
const scene = new THREE.Scene();

// light
const light = new THREE.DirectionalLight(0xffffff, Math.PI);
scene.add(light);

// ========================
// AUDIO WEBSOCKET
// ========================

const audioSocket = new WebSocket("ws://localhost:8080");
audioSocket.binaryType = "arraybuffer";

audioSocket.onopen = () => {
  console.log("Connected to audio server");
  audioSocket.send("browser");
};

audioSocket.onmessage = (event) => {
  const pcm = new Int16Array(event.data);
  playChunk(pcm);
};

audioSocket.onclose = () => {
  console.log("Audio websocket closed");
};

// Allow browser audio after user interaction
window.addEventListener("click", () => {
  if (audioContext.state === "suspended") {
    audioContext.resume();
  }
});

// ========================
// VRM & ANIMATION LOADING
// ========================

let currentVrm = undefined;
let mixer = undefined;

const loader = new GLTFLoader();
loader.crossOrigin = "anonymous";
loader.register((parser) => {
  return new VRMLoaderPlugin(parser);
});

loader.load(
  "public/models/model.vrm",
  (gltf) => {
    const vrm = gltf.userData.vrm;

    VRMUtils.removeUnnecessaryVertices(gltf.scene);
    VRMUtils.combineSkeletons(gltf.scene);

    vrm.scene.traverse((obj) => {
      obj.frustumCulled = false;
    });

    currentVrm = vrm;
    scene.add(vrm.scene);

    mixer = new THREE.AnimationMixer(vrm.scene);

    const fbxLoader = new FBXLoader();
    fbxLoader.load("public/animations/idle.fbx", (fbx) => {
      const clip = retargetAnimation(fbx, vrm);

      if (clip) {
        const action = mixer.clipAction(clip);
        action.play();
      }
    });
  },
  (progress) =>
    console.log(
      "Loading model...",
      100.0 * (progress.loaded / progress.total),
      "%",
    ),
  (error) => console.error(error),
);

// ========================
// AUDIO PLAYBACK
// ========================

function playChunk(pcm) {
  const float32 = new Float32Array(pcm.length);

  for (let i = 0; i < pcm.length; i++) {
    float32[i] = pcm[i] / 32768;
  }

  const buffer = audioContext.createBuffer(1, float32.length, 24000);
  buffer.copyToChannel(float32, 0);

  const source = audioContext.createBufferSource();
  source.buffer = buffer;

  // Connect to the analyser for real-time lip sync reading
  source.connect(analyser);

  if (nextAudioTime < audioContext.currentTime) {
    nextAudioTime = audioContext.currentTime;
  }

  source.start(nextAudioTime);
  nextAudioTime += buffer.duration;
}

// ========================
// ANIMATION LOOP
// ========================

const clock = new THREE.Clock();
clock.start();

let nextBlinkTime = 0;

function animate() {
  requestAnimationFrame(animate);

  if (currentVrm) {
    const delta = clock.getDelta();

    // 1. UPDATE BODY ANIMATION FIRST
    if (mixer) {
      mixer.update(delta);
    }

    // 2. CALCULATE REAL-TIME AUDIO PEAKS
    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteTimeDomainData(dataArray);

    let peak = 0;
    for (let i = 0; i < dataArray.length; i++) {
      // Convert 0-255 range to 0.0-1.0
      const sample = Math.abs(dataArray[i] - 128) / 128;
      if (sample > peak) {
        peak = sample;
      }
    }

    // Scale peak slightly
    targetMouthValue = Math.min(1, peak * 3);

    // 3. APPLY FACE EXPRESSIONS
    if (currentVrm.expressionManager) {
      // Smooth mouth movement
      currentMouthValue += (targetMouthValue - currentMouthValue) * 0.3;

      // Handle both VRM 1.0 ("aa") and VRM 0.0 ("a") naming conventions
      const mouthExpression = currentVrm.expressionManager.getExpression("aa")
        ? "aa"
        : "a";
      currentVrm.expressionManager.setValue(mouthExpression, currentMouthValue);

      // Apply blink
      const t = clock.elapsedTime;

      if (t > nextBlinkTime) {
        currentVrm.expressionManager.setValue("blink", 1.0);
        nextBlinkTime = t + 2 + Math.random() * 4;
      } else {
        const currentBlink = currentVrm.expressionManager.getValue("blink");
        if (currentBlink > 0) {
          currentVrm.expressionManager.setValue(
            "blink",
            Math.max(0, currentBlink - 0.1),
          );
        }
      }
    }

    // 4. UPDATE VRM LAST
    // Automatically handles pushing the expressions and updating springbones
    // against the new Mixamo rig positions.
    currentVrm.update(delta);
  }

  renderer.render(scene, camera);
}

animate();
