import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { VRMLoaderPlugin, VRMUtils } from "@pixiv/three-vrm";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";
import { retargetAnimation } from "vrm-mixamo-retarget";

import { setExpression } from "./charController.js";

// ========================
// AUDIO STREAMING & LIP SYNC
// ========================

const audioContext = new AudioContext({
  sampleRate: 24000,
});

let nextAudioTime = 0;

const analyser = audioContext.createAnalyser();
analyser.fftSize = 512; // Increased size for better frequency separation
analyser.connect(audioContext.destination);

// Create a proper THREE.Object3D to act as the look-at target for the VRM
const lookAtTarget = new THREE.Object3D();

const character = {
  // Multi-viseme tracking weights
  mouthValues: {
    aa: 0, // Open / Low frequencies (e.g., "ah")
    ih: 0, // Mid-high frequencies (e.g., "ee", "ih")
    ou: 0, // Pursed / Rounded lips (e.g., "oo", "oh")
  },
  targetMouthValues: {
    aa: 0,
    ih: 0,
    ou: 0,
  },
  nextBlinkTime: 0,
  setExpression,
  currentExpression: "neutral",
  expressionWeights: {},
  targetExpressionWeights: {},

  // Custom Expression Presets (combining multiple VRM blendshapes for a richer look)
  customExpressions: {
    neutral: {
      happy: 0.0,
      relaxed: 0.0,
      sad: 0.0,
      angry: 0.0,
      surprised: 0.0,
      ih: 0.0,
    },
    customHappy: {
      happy: 0.8, // Primary joyful expression
      relaxed: 0.35, // Softens/squints the eyes for a genuine "Duchenne" smile
      ih: 0.2, // Widens the mouth corners slightly
    },
  },

  // Helper to trigger a custom expression by name
  setCustomExpression(name) {
    const preset =
      this.customExpressions[name] || this.customExpressions.neutral;
    this.currentExpression = name;

    for (const [key, value] of Object.entries(preset)) {
      this.targetExpressionWeights[key] = value;
    }
  },

  nextGazeTime: 0,
  isSpeaking: false,
  // Temporary storage vectors for smooth interpolation
  targetPosition: new THREE.Vector3(),
};

// ========================
// THREE.JS SETUP
// ========================

const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.body.appendChild(renderer.domElement);

const camera = new THREE.PerspectiveCamera(
  30.0,
  window.innerWidth / window.innerHeight,
  0.1,
  20.0,
);
camera.position.set(0.0, 1.0, 5.0);

const controls = new OrbitControls(camera, renderer.domElement);
controls.screenSpacePanning = true;
controls.target.set(0.0, 1.0, 0.0);
controls.update();

const scene = new THREE.Scene();
scene.add(lookAtTarget); // Add target object to the scene graph

const light = new THREE.DirectionalLight(0xffffff, Math.PI);
scene.add(light);

// ========================
// AUDIO WEBSOCKET
// ========================

const audioSocket = new WebSocket("ws://localhost:3000");
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

window.addEventListener("click", () => {
  if (audioContext.state === "suspended") {
    audioContext.resume();
  }
});

// ========================
// CONTROL WEBSOCKET
// ========================
const controlSocket = new WebSocket("ws://localhost:3001");

controlSocket.onopen = () => {
  console.log("connected");
  controlSocket.send("hello");
};

controlSocket.onmessage = (event) => {
  console.log("received:", event.data);
  const data = JSON.parse(event.data);

  // Sentence-by-sentence subtitle, timed to when its audio starts
  if (data.type === "subtitle") {
    queueSubtitle(data.text);
    return;
  }

  // User started talking: stop Yuna's audio immediately
  if (data.type === "stop_audio") {
    stopAudio();
    return;
  }

  // Yuna is thinking (tool execution in progress)
  if (data.type === "status") {
    displayStatus(data.text);
    return;
  }

  const { facial_expression, response, pose } = data;
  character.setExpression(facial_expression.toLowerCase());

  // Switch body pose (e.g. "thinking", "happy") with a smooth crossfade
  if (pose) {
    playPose(pose.toLowerCase());
  }

  // Fallback: if no sentence subtitles were queued for this turn, display
  // the full response instead.
  if (!subtitlesQueued) {
    displaySubtitles(response);
  }
  subtitlesQueued = false;
};

// ========================
// MODE TOGGLE (assistant / companion)
// ========================
const modeToggle = document.querySelector("#mode-toggle");
let currentMode = "assistant";

modeToggle.addEventListener("click", () => {
  currentMode = currentMode === "assistant" ? "companion" : "assistant";
  modeToggle.textContent =
    currentMode === "assistant" ? "Assistant" : "Companion";
  modeToggle.classList.toggle("companion", currentMode === "companion");
  if (controlSocket.readyState === WebSocket.OPEN) {
    controlSocket.send(JSON.stringify({ type: "mode", mode: currentMode }));
  }
});

// ========================
// SUBTITLES (SYNCED WITH AUDIO)
// ========================

// Each subtitle is queued with the audioContext time at which its
// sentence's audio starts playing, and shown at exactly that moment.
const subtitleQueue = [];
let subtitlesQueued = false;

// Whether a spoken subtitle is currently on screen, and when it was shown.
// Used to fade the subtitle out a few seconds after Yuna finishes speaking.
let subtitleVisible = false;
let subtitleShownAt = 0;
const SUBTITLE_FADE_DELAY = 1.0; // seconds after the last audio ends

function queueSubtitle(text) {
  // The sentence's audio chunks are sent right after this message, so
  // nextAudioTime is exactly when this sentence will start playing.
  const startTime = Math.max(nextAudioTime, audioContext.currentTime);
  subtitleQueue.push({ text, startTime });
  subtitlesQueued = true;
}

function updateSubtitles() {
  const now = audioContext.currentTime;
  while (subtitleQueue.length && subtitleQueue[0].startTime <= now) {
    const { text } = subtitleQueue.shift();
    displaySubtitles(text);
  }
}

function displaySubtitles(text) {
  const subHolder = document.querySelector("#subtitles")
  while(subHolder.hasChildNodes()) {
    subHolder.removeChild(subHolder.firstChild)
  }
  const sub = document.createElement("p");
  sub.innerText = text;
  subHolder.appendChild(sub);
  subtitleVisible = true;
  subtitleShownAt = audioContext.currentTime;
}

function displayStatus(text) {
  const subHolder = document.querySelector("#subtitles");
  while (subHolder.hasChildNodes()) {
    subHolder.removeChild(subHolder.firstChild);
  }
  const sub = document.createElement("p");
  sub.classList.add("status");
  sub.innerText = text;
  subHolder.appendChild(sub);
  // The status is not spoken dialogue; it is replaced by the next subtitle.
  subtitleVisible = false;
}

// Fade out and clear the current subtitle.
function hideSubtitles() {
  const subHolder = document.querySelector("#subtitles");
  const sub = subHolder.querySelector("p");
  if (sub) {
    sub.classList.add("fade-out");
    setTimeout(() => {
      subHolder.innerHTML = "";
    }, 500);
  }
}

// ========================
// KEYBOARD CONTROLS (TESTING EXPRESSIONS)
// ========================

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (key === "h") {
    console.log("Expression: customHappy");
    character.setCustomExpression("customHappy");
    console.log('expressionWeights', character.expressionWeights);
    console.log('targetExpressionWeights', character.targetExpressionWeights);
  } else if (key === "n") {
    console.log("Expression: neutral");
    character.setCustomExpression("neutral");
    console.log('expressionWeights', character.expressionWeights);
    console.log('targetExpressionWeights', character.targetExpressionWeights);
  } else if (key === "s") {
    console.log("Expression: neutral");
    console.log('expressionWeights', character.expressionWeights);
    console.log('targetExpressionWeights', character.targetExpressionWeights);
    character.setExpression("sad");
  } else if (key === "j") {
    character.setExpression("happy");
    console.log('expressionWeights', character.expressionWeights);
    console.log('targetExpressionWeights', character.targetExpressionWeights);
  } else if (key === "t") {
    console.log("netural");

    character.setExpression("neutral");
    console.log('expressionWeights', character.expressionWeights);
    console.log('targetExpressionWeights', character.targetExpressionWeights);
  }
});

// ========================
// VRM & ANIMATION LOADING
// ========================

let currentVrm = undefined;
let mixer = undefined;

// ========================
// POSES (FBX ANIMATIONS)
// ========================

const POSES = [
  "idle",
  "happy",
  "excited",
  "angry",
  "thinking",
  "thankful",
  "rejected",
  "terrified",
  "yawn",
  "standing_greeting",
  "idletofight",
];

const poseActions = {};
let currentPoseAction = null;

// Crossfade from the current pose to the requested one. Falls back to
// idle if the requested pose failed to load.
function playPose(name) {
  const action = poseActions[name] || poseActions.idle;
  if (!action || action === currentPoseAction) return;
  action.reset().play();
  if (currentPoseAction) {
    currentPoseAction.crossFadeTo(action, 0.4, false);
  }
  currentPoseAction = action;
}

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
    console.log(vrm);
    mixer = new THREE.AnimationMixer(vrm.scene);

    // Assign lookAt target directly using the native object
    if (vrm.lookAt) {
      vrm.lookAt.target = lookAtTarget;
    }

    // Load and retarget every pose, then start with idle.
    const fbxLoader = new FBXLoader();
    let loadedPoses = 0;

    const finishLoadingPoses = () => {
      loadedPoses++;
      if (loadedPoses < POSES.length) return;
      playPose("idle");
      scene.add(vrm.scene);
    };

    for (const pose of POSES) {
      fbxLoader.load(
        `public/animations/${pose}.fbx`,
        (fbx) => {
          const clip = retargetAnimation(fbx, vrm);
          if (clip) {
            poseActions[pose] = mixer.clipAction(clip);
          } else {
            console.warn(`Pose retarget failed: ${pose}`);
          }
          finishLoadingPoses();
        },
        undefined,
        (error) => {
          console.error(`Failed to load pose ${pose}`, error);
          finishLoadingPoses();
        },
      );
    }
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

// Sources currently playing (or scheduled to play) so we can stop them
// immediately when the user interrupts.
const activeSources = new Set();

// Whether we have told Python that audio is currently playing. The browser
// may keep playing after Python finished streaming, so Python relies on
// this to know when Yuna is actually audible (for interruption gating).
let playbackReported = false;

function updatePlaybackState() {
  const playing = activeSources.size > 0;
  if (playing === playbackReported) return;
  playbackReported = playing;
  if (controlSocket.readyState === WebSocket.OPEN) {
    controlSocket.send(JSON.stringify({ type: "playing", playing }));
  }
}

function playChunk(pcm) {
  const float32 = new Float32Array(pcm.length);

  for (let i = 0; i < pcm.length; i++) {
    float32[i] = pcm[i] / 32768;
  }

  const buffer = audioContext.createBuffer(1, float32.length, 24000);
  buffer.copyToChannel(float32, 0);

  const source = audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(analyser);

  if (nextAudioTime < audioContext.currentTime) {
    nextAudioTime = audioContext.currentTime;
  }

  source.start(nextAudioTime);
  nextAudioTime += buffer.duration;

  activeSources.add(source);
  source.onended = () => {
    activeSources.delete(source);
    updatePlaybackState();
  };
  updatePlaybackState();
}

// Stop all current and scheduled audio playback (used for interruption).
function stopAudio() {
  for (const source of activeSources) {
    try {
      source.stop();
    } catch (e) {
      // Already stopped
    }
  }
  activeSources.clear();
  updatePlaybackState();

  // Drop any subtitles that were queued but not yet shown
  subtitleQueue.length = 0;

  // Reschedule future chunks from "now" so the next sentence starts
  // immediately instead of after the old (now cancelled) timeline.
  nextAudioTime = audioContext.currentTime;
}

// ========================
// EXPRESSION & BLINKING UTILS
// ========================

function updateCustomExpressions(delta, character, vrm) {
  if (!vrm.expressionManager) return;

  const speed = 6.0;
  const lerpFactor = Math.min(1.0, delta * speed);

  for (const [key, targetValue] of Object.entries(
    character.targetExpressionWeights,
  )) {
    if (character.expressionWeights[key] === undefined) {
      character.expressionWeights[key] = 0;
    }

    character.expressionWeights[key] +=
      (targetValue - character.expressionWeights[key]) * lerpFactor;

    const exprName = vrm.expressionManager.getExpression(key) ? key : null;
    if (exprName) {
      vrm.expressionManager.setValue(
        exprName,
        character.expressionWeights[key],
      );
    }
  }
}

function blinking(t, character) {
  if (t > character.nextBlinkTime) {
    currentVrm.expressionManager.setValue("blink", 1.0);
    character.nextBlinkTime = t + 2 + Math.random() * 4;
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

// ========================
// ANIMATION LOOP
// ========================

const clock = new THREE.Clock();
clock.start();

function animate() {
  requestAnimationFrame(animate);

  if (currentVrm) {
    // Clamp delta to a maximum of 0.1s (10 FPS equivalent) to prevent
    // large time jumps when returning to an inactive browser tab
    const rawDelta = clock.getDelta();
    const delta = Math.min(rawDelta, 0.1);
    const t = clock.elapsedTime;

    if (mixer) {
      mixer.update(delta);
    }

    // Show the next subtitle at the exact moment its audio starts
    updateSubtitles();

    // Tell Python when playback actually ends (covers the case where the
    // last source finishes between frames).
    updatePlaybackState();

    // Fade out the subtitle a few seconds after Yuna finishes speaking.
    // nextAudioTime is when the last audio chunk ends; subtitleShownAt covers
    // the case where a subtitle is shown without audio.
    if (subtitleVisible) {
      const referenceTime = Math.max(nextAudioTime, subtitleShownAt);
      if (audioContext.currentTime > referenceTime + SUBTITLE_FADE_DELAY) {
        hideSubtitles();
        subtitleVisible = false;
      }
    }

    // Advanced Multi-Band Frequency Audio Analysis for Visemes
    const frequencyData = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(frequencyData);

    // Split frequency spectrum into distinct functional bins
    let lowSum = 0,
      midSum = 0,
      highSum = 0;
    const third = Math.floor(frequencyData.length / 3);

    for (let i = 0; i < third; i++) lowSum += frequencyData[i];
    for (let i = third; i < third * 2; i++) midSum += frequencyData[i];
    for (let i = third * 2; i < frequencyData.length; i++)
      highSum += frequencyData[i];

    const lowEnergy = lowSum / third / 255;
    const midEnergy = midSum / third / 255;
    const highEnergy = highSum / third / 255;

    // Map frequency energy distributions to distinct mouth shapes (visemes)
    character.targetMouthValues.aa = Math.min(1, lowEnergy * 2.5); // Open jaw / deep sounds
    character.targetMouthValues.ih = Math.min(1, midEnergy * 2.5); // Wide smile/spread sounds
    character.targetMouthValues.ou = Math.min(1, highEnergy * 2.0); // Rounded / pursed mouth sounds

    const overallEnergy = (lowEnergy + midEnergy + highEnergy) / 3;
    character.isSpeaking = overallEnergy > 0.03;

    // Face Expressions & Multi-Viseme Lip Sync
    if (currentVrm.expressionManager) {
      const lerpFactor = Math.min(1.0, delta * 15.0); // Responsive interpolation speed, clamped

      // Smoothly update each viseme value
      for (const viseme of ["aa", "ih", "ou"]) {
        character.mouthValues[viseme] +=
          (character.targetMouthValues[viseme] -
            character.mouthValues[viseme]) *
          lerpFactor;

        // Check if VRM model supports the specific shape name, fallback gracefully
        const shapeName = currentVrm.expressionManager.getExpression(viseme)
          ? viseme
          : viseme === "ou"
            ? "oh"
            : "a";
        currentVrm.expressionManager.setValue(
          shapeName,
          character.mouthValues[viseme],
        );
      }

      updateCustomExpressions(delta, character, currentVrm);
      blinking(t, character);
    }

    // Gaze Logic: Look at camera when talking, wander when idle
    if (character.isSpeaking) {
      character.targetPosition.copy(camera.position);
    } else {
      if (t > character.nextGazeTime) {
        const randomX = (Math.random() - 0.5) * 1.5;
        const randomY = (Math.random() - 0.5) * 0.8;

        character.targetPosition.copy(camera.position);
        character.targetPosition.x += randomX;
        character.targetPosition.y += randomY;

        character.nextGazeTime = t + 1.5 + Math.random() * 3.0;
      }
    }

    // Smoothly lerp the dummy target object's position (clamped to prevent overshoot)
    lookAtTarget.position.lerp(
      character.targetPosition,
      Math.min(1.0, delta * 4.0),
    );

    currentVrm.update(delta);
  }

  renderer.render(scene, camera);
}

animate();