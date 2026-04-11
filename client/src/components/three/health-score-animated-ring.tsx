import { useRef, useState, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Html, OrbitControls } from '@react-three/drei'

interface HealthScoreRingProps {
  score?: number
}

function scoreColor(score: number): string {
  if (score <= 33) return '#ef4444'
  if (score <= 66) return '#f59e0b'
  return '#22c55e'
}

export function HealthScoreRing({ score = 45 }: HealthScoreRingProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const arcRef = useRef(0)
  const targetArc = (Math.min(100, Math.max(0, score)) / 100) * Math.PI * 2

  // Animate arc from 0 to target on mount
  useEffect(() => {
    arcRef.current = 0
  }, [score])

  useFrame((_, delta) => {
    if (!meshRef.current) return
    const prev = arcRef.current
    if (prev < targetArc) {
      arcRef.current = Math.min(targetArc, prev + delta * 2.5)
      const geo = new THREE.TorusGeometry(1.4, 0.28, 16, 64, arcRef.current)
      meshRef.current.geometry.dispose()
      meshRef.current.geometry = geo
    }
  })

  const color = scoreColor(score)
  const initialGeo = new THREE.TorusGeometry(1.4, 0.28, 16, 64, 0.01)

  return (
    <group>
      {/* Background ring (track) */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.4, 0.28, 16, 64, Math.PI * 2]} />
        <meshStandardMaterial color="#1e293b" roughness={0.6} metalness={0.2} transparent opacity={0.5} />
      </mesh>

      {/* Animated fill ring */}
      <mesh ref={meshRef} geometry={initialGeo} rotation={[Math.PI / 2, 0, -Math.PI / 2]}>
        <meshStandardMaterial
          color={color}
          roughness={0.2}
          metalness={0.6}
          emissive={color}
          emissiveIntensity={0.3}
        />
      </mesh>

      {/* Score label in center */}
      <Html center>
        <div style={{ textAlign: 'center', userSelect: 'none' }}>
          <div style={{ fontSize: 28, fontWeight: 700, color, lineHeight: 1 }}>{score}</div>
          <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>Health Score</div>
        </div>
      </Html>

      <OrbitControls
        enableZoom
        enablePan={false}
        minDistance={3}
        maxDistance={8}
        autoRotate={false}
      />
    </group>
  )
}
