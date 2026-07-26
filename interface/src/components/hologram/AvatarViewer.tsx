/*
 * MADE By Manoj Dahal
 * Copyright (c) 2026 Manoj Dahal. All rights reserved.
 * Contact: info@manoj-dahal.com.np
 * AERA — Artificial Enhanced Reasoning Assistant
 */

import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { emotionColors, type Emotion } from '@design/colors';
import type { SphereState } from './ParticleSphere';

export interface AvatarViewerProps {
  /** Model id from the avatar library; null renders nothing. */
  modelId: string | null;
  /** Format, used to pick the loader. */
  format?: string;
  state?: SphereState;
  emotion?: string;
  size?: number;
  /** 0..1 audio level, drives the speaking bob. */
  level?: number;
  className?: string;
  onError?: (message: string) => void;
  onLoaded?: (info: { triangles: number; seconds: number }) => void;
}

/** Motion profile per avatar state, mirroring the particle sphere. */
const PROFILES: Record<SphereState, { spin: number; bob: number; rim: number; sway: number }> = {
  idle:       { spin: 0.10, bob: 0.004, rim: 0.35, sway: 0.010 },
  listening:  { spin: 0.14, bob: 0.008, rim: 0.75, sway: 0.016 },
  thinking:   { spin: 0.30, bob: 0.006, rim: 0.60, sway: 0.022 },
  speaking:   { spin: 0.12, bob: 0.020, rim: 0.95, sway: 0.014 },
  processing: { spin: 0.40, bob: 0.006, rim: 0.80, sway: 0.018 },
  error:      { spin: 0.04, bob: 0.003, rim: 0.50, sway: 0.006 },
  offline:    { spin: 0.02, bob: 0.000, rim: 0.10, sway: 0.002 },
};

/**
 * Renders a user-supplied avatar model with three.js.
 *
 * The model is fetched from `/api/v1/avatars/{id}/file`, normalised to a
 * consistent on-screen size regardless of its authored units, and lit with a
 * three-point rig plus an emotion-tinted rim light. Rotation, breathing and
 * sway follow the same state machine as the particle sphere, so the two are
 * interchangeable in the dashboard.
 */
export function AvatarViewer({
  modelId,
  format = 'glb',
  state = 'idle',
  emotion = 'neutral',
  size = 320,
  level = 0,
  className,
  onError,
  onLoaded,
}: AvatarViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  // Live refs so prop changes never tear down the render loop.
  const stateRef = useRef(state);
  const emotionRef = useRef(emotion);
  const levelRef = useRef(level);
  stateRef.current = state;
  emotionRef.current = emotion;
  levelRef.current = level;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || !modelId) return;

    let disposed = false;
    const started = performance.now();
    setLoading(true);
    setFailed(null);

    // ---- scene -------------------------------------------------------
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.01, 100);
    camera.position.set(0, 0, 3.1);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(size, size);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    // ---- lighting: three-point plus an emotion rim -------------------
    scene.add(new THREE.AmbientLight(0x404a5c, 1.4));

    const key = new THREE.DirectionalLight(0xffffff, 2.1);
    key.position.set(2, 3, 3);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0x7c9fd0, 0.7);
    fill.position.set(-3, 0.5, 2);
    scene.add(fill);

    const rim = new THREE.DirectionalLight(0x4da6ff, 1.6);
    rim.position.set(-1.5, 2, -3);
    scene.add(rim);

    // Ground bounce keeps the underside from going pure black.
    const bounce = new THREE.DirectionalLight(0x2a3550, 0.5);
    bounce.position.set(0, -3, 1);
    scene.add(bounce);

    const pivot = new THREE.Group();
    scene.add(pivot);

    // ---- loading -----------------------------------------------------
    const url = `/api/v1/avatars/${encodeURIComponent(modelId)}/file`;

    /** Centre the model and scale it to a consistent on-screen height. */
    const fit = (object: THREE.Object3D) => {
      const box = new THREE.Box3().setFromObject(object);
      const extent = new THREE.Vector3();
      box.getSize(extent);
      const centre = new THREE.Vector3();
      box.getCenter(centre);

      const tallest = Math.max(extent.x, extent.y, extent.z);
      if (tallest > 0) {
        // Authored units vary wildly (mm, cm, m); normalise to ~2 units.
        object.scale.multiplyScalar(2.0 / tallest);
      }
      object.position.sub(centre.multiplyScalar(object.scale.x));
      pivot.add(object);

      let triangles = 0;
      object.traverse((child) => {
        const mesh = child as THREE.Mesh;
        if (!mesh.isMesh) return;
        const geometry = mesh.geometry;
        const position = geometry.attributes.position;
        if (geometry.index) {
          triangles += geometry.index.count / 3;
        } else if (position) {
          triangles += position.count / 3;
        }
        // Models often ship without normals; without these they render flat black.
        if (position && !geometry.attributes.normal) geometry.computeVertexNormals();
      });

      if (!disposed) {
        setLoading(false);
        onLoaded?.({
          triangles: Math.round(triangles),
          seconds: (performance.now() - started) / 1000,
        });
      }
    };

    const fail = (message: string) => {
      if (disposed) return;
      setLoading(false);
      setFailed(message);
      onError?.(message);
    };

    const extension = format.toLowerCase();
    if (extension === 'glb' || extension === 'gltf') {
      new GLTFLoader().load(
        url,
        (gltf) => !disposed && fit(gltf.scene),
        undefined,
        (error) => fail(`could not load model: ${(error as Error).message ?? 'unknown error'}`),
      );
    } else if (extension === 'obj') {
      // Try the sidecar MTL first; fall back to a default material when absent.
      const mtlUrl = url.replace(/\/file$/, '/material');
      new MTLLoader().load(
        mtlUrl,
        (materials) => {
          materials.preload();
          const loader = new OBJLoader();
          loader.setMaterials(materials);
          loader.load(url, (object) => !disposed && fit(object), undefined, () =>
            fail('could not load the OBJ geometry'),
          );
        },
        undefined,
        () => {
          new OBJLoader().load(
            url,
            (object) => {
              object.traverse((child) => {
                const mesh = child as THREE.Mesh;
                if (mesh.isMesh) {
                  mesh.material = new THREE.MeshStandardMaterial({
                    color: 0xc9d4e6,
                    roughness: 0.62,
                    metalness: 0.06,
                  });
                }
              });
              if (!disposed) fit(object);
            },
            undefined,
            () => fail('could not load the OBJ geometry'),
          );
        },
      );
    } else {
      fail(`${extension.toUpperCase()} cannot be rendered in the browser; export to GLB`);
    }

    // ---- animation ---------------------------------------------------
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    let frame = 0;
    let raf = 0;

    const tick = () => {
      const profile = PROFILES[stateRef.current] ?? PROFILES.idle;
      const colour = emotionColors[emotionRef.current as Emotion] ?? emotionColors.neutral;
      const audio = Math.max(0, Math.min(1, levelRef.current));

      frame += 1;
      pivot.rotation.y += profile.spin * 0.01;
      // Breathing, amplified while speaking by the audio level.
      pivot.position.y = Math.sin(frame * 0.03) * profile.bob * (1 + audio * 2);
      pivot.rotation.z = Math.sin(frame * 0.017) * profile.sway;

      rim.color.set(colour);
      rim.intensity = profile.rim * (1 + audio * 0.5);

      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };

    if (reduceMotion) {
      renderer.render(scene, camera);
    } else {
      raf = requestAnimationFrame(tick);
    }

    // ---- teardown ------------------------------------------------------
    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      // Three.js does not free GPU memory on garbage collection; disposing
      // explicitly prevents a leak every time the model changes.
      scene.traverse((child) => {
        const mesh = child as THREE.Mesh;
        if (!mesh.isMesh) return;
        mesh.geometry?.dispose();
        const material = mesh.material;
        if (Array.isArray(material)) material.forEach((m) => m.dispose());
        else material?.dispose();
      });
      renderer.dispose();
      if (renderer.domElement.parentNode === mount) {
        mount.removeChild(renderer.domElement);
      }
    };
  }, [modelId, format, size, onError, onLoaded]);

  if (!modelId) return null;

  return (
    <div className={className} style={{ width: size, height: size, position: 'relative' }}>
      <div ref={mountRef} style={{ width: size, height: size }} />
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center text-[11.5px] text-[var(--aera-text-muted)]">
          Loading model…
        </div>
      )}
      {failed && (
        <div className="absolute inset-0 flex items-center justify-center p-4 text-center text-[11.5px] text-[var(--aera-danger)]">
          {failed}
        </div>
      )}
    </div>
  );
}
