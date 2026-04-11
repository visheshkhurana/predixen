import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { OrbitControls, Line, Html } from '@react-three/drei'

interface Branch {
  label: string
  color: string
  end: [number, number, number]
}

const BRANCHES: Branch[] = [
  { label: 'Hire Engineers', color: '#22c55e', end: [2.5, 1.5, 0] },
  { label: 'Raise Series A', color: '#f59e0b', end: [2.8, 0, 0] },
  { label: 'Stay Course',    color: '#ef4444', end: [2.5, -1.5, 0] },
]

const ROOT: [number, number, number] = [0, 0, 0]

function NodeSphere({
  position,
  color,
  radius = 0.18,
}: {
  position: [number, number, number]
  color: string
  radius?: number
}) {
  return (
    <mesh position={position}>
      <sphereGeometry args={[radius, 16, 16]} />
      <meshStandardMaterial color={color} roughness={0.3} metalness={0.4} />
    </mesh>
  )
}

export function DecisionTree3D() {
  const groupRef = useRef<THREE.Group>(null)

  useFrame((_, delta) => {
    if (groupRef.current) groupRef.current.rotation.y += delta * 0.12
  })

  return (
    <group ref={groupRef}>
      {/* Root node */}
      <NodeSphere position={ROOT} color="#e2e8f0" radius={0.22} />
      <Html position={[0, 0.42, 0]} center>
        <span style={{ fontSize: 10, color: '#94a3b8', whiteSpace: 'nowrap', userSelect: 'none' }}>
          Decision Point
        </span>
      </Html>

      {BRANCHES.map((b) => (
        <group key={b.label}>
          {/* Branch line */}
          <Line
            points={[ROOT, b.end]}
            color={b.color}
            lineWidth={2}
            transparent
            opacity={0.7}
          />

          {/* End node */}
          <NodeSphere position={b.end} color={b.color} />

          {/* Label */}
          <Html position={[b.end[0] + 0.1, b.end[1] + 0.32, b.end[2]]} center>
            <span
              style={{
                fontSize: 10,
                color: b.color,
                whiteSpace: 'nowrap',
                fontWeight: 600,
                userSelect: 'none',
                textShadow: '0 1px 4px rgba(0,0,0,0.8)',
              }}
            >
              {b.label}
            </span>
          </Html>
        </group>
      ))}

      <OrbitControls
        enableZoom
        enablePan={false}
        minDistance={4}
        maxDistance={12}
        autoRotate={false}
      />
    </group>
  )
}
