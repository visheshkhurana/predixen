// @ts-nocheck — R3F extends JSX.IntrinsicElements which conflicts with React's strict types
import { useRef, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Float, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

/** Animated distorted sphere — organic 3D accent */
function DistortedSphere({
  position,
  color,
  scale,
  speed,
}: {
  position: [number, number, number];
  color: string;
  scale: number;
  speed: number;
}) {
  const mesh = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (mesh.current) {
      mesh.current.rotation.x += delta * speed * 0.1;
      mesh.current.rotation.y += delta * speed * 0.15;
    }
  });

  return (
    <Float speed={speed} rotationIntensity={0.3} floatIntensity={0.5}>
      <mesh ref={mesh} position={position} scale={scale}>
        <icosahedronGeometry args={[1, 4]} />
        <MeshDistortMaterial
          color={color}
          transparent
          opacity={0.12}
          distort={0.4}
          speed={1.5}
          roughness={0.8}
        />
      </mesh>
    </Float>
  );
}

/** Floating particle field — subtle depth particles */
function ParticleField({ count = 80 }: { count?: number }) {
  const points = useMemo(() => {
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 10;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 5;
    }
    return positions;
  }, [count]);

  const ref = useRef<THREE.Points>(null);

  useFrame((_, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.02;
      ref.current.rotation.x += delta * 0.01;
    }
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          args={[points, 3]}
        />
      </bufferGeometry>
      <pointsMaterial
        size={0.02}
        color="#6366f1"
        transparent
        opacity={0.4}
        sizeAttenuation
      />
    </points>
  );
}

/** Full 3D background canvas — place behind dashboard content */
export function ThreeDimensionalMeshBackground({
  className,
  variant = "default",
}: {
  className?: string;
  variant?: "default" | "minimal" | "finance";
}) {
  const configs = {
    default: {
      spheres: [
        { position: [-2, 1, -2] as [number, number, number], color: "#6366f1", scale: 1.5, speed: 1.2 },
        { position: [2.5, -0.5, -3] as [number, number, number], color: "#22c55e", scale: 1, speed: 0.8 },
        { position: [0, -1.5, -2.5] as [number, number, number], color: "#8b5cf6", scale: 0.8, speed: 1.5 },
      ],
      particles: 80,
    },
    minimal: {
      spheres: [
        { position: [-1.5, 0.5, -3] as [number, number, number], color: "#6366f1", scale: 1.2, speed: 0.6 },
      ],
      particles: 40,
    },
    finance: {
      spheres: [
        { position: [-2, 1, -2] as [number, number, number], color: "#22c55e", scale: 1.3, speed: 1 },
        { position: [2, -1, -3] as [number, number, number], color: "#ef4444", scale: 0.9, speed: 1.3 },
        { position: [0, 0, -4] as [number, number, number], color: "#6366f1", scale: 1.6, speed: 0.7 },
      ],
      particles: 100,
    },
  };

  const config = configs[variant];

  return (
    <div className={`pointer-events-none absolute inset-0 ${className ?? ""}`}>
      <Canvas
        camera={{ position: [0, 0, 5], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 5, 5]} intensity={0.3} />
        {config.spheres.map((sphere, i) => (
          <DistortedSphere key={i} {...sphere} />
        ))}
        <ParticleField count={config.particles} />
      </Canvas>
    </div>
  );
}
