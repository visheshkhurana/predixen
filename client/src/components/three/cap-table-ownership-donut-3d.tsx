import { useRef, useState } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { Html } from '@react-three/drei'

interface Stakeholder {
  label: string
  percent: number
  color: string
}

const STAKEHOLDERS: Stakeholder[] = [
  { label: 'Founders', percent: 60, color: '#6366f1' },
  { label: 'Investors', percent: 25, color: '#8b5cf6' },
  { label: 'ESOP',      percent: 10, color: '#06b6d4' },
  { label: 'Advisors',  percent: 5,  color: '#f59e0b' },
]

const TORUS_RADIUS = 1.6
const TUBE_RADIUS  = 0.38
const GAP_RADIANS  = 0.06

function buildSegmentArc(startAngle: number, endAngle: number): THREE.TorusGeometry {
  const arc = endAngle - startAngle - GAP_RADIANS
  const geo = new THREE.TorusGeometry(TORUS_RADIUS, TUBE_RADIUS, 16, 64, Math.max(0.01, arc))
  return geo
}

interface SegmentProps {
  stakeholder: Stakeholder
  startAngle: number
  endAngle: number
  index: number
}

function DonutSegment({ stakeholder, startAngle, endAngle, index }: SegmentProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const [hovered, setHovered] = useState(false)

  const geo = buildSegmentArc(startAngle, endAngle)
  const midAngle = (startAngle + endAngle) / 2

  const labelX = Math.cos(midAngle) * (TORUS_RADIUS + 0.9)
  const labelY = Math.sin(midAngle) * (TORUS_RADIUS + 0.9)

  useFrame(() => {
    if (!meshRef.current) return
    const target = hovered ? 1.12 : 1.0
    meshRef.current.scale.lerp(new THREE.Vector3(target, target, target), 0.12)
  })

  return (
    <group rotation={[Math.PI / 2, 0, startAngle]}>
      <mesh
        ref={meshRef}
        geometry={geo}
        onPointerEnter={() => setHovered(true)}
        onPointerLeave={() => setHovered(false)}
      >
        <meshStandardMaterial
          color={stakeholder.color}
          roughness={0.3}
          metalness={0.5}
          transparent
          opacity={hovered ? 1 : 0.85}
        />
      </mesh>

      <Html
        position={[
          Math.cos(0) * (TORUS_RADIUS + 0.9),
          0,
          -Math.sin(0) * (TORUS_RADIUS + 0.9),
        ]}
        center
      >
        <div
          style={{
            fontSize: 10,
            color: stakeholder.color,
            fontWeight: 600,
            whiteSpace: 'nowrap',
            userSelect: 'none',
            textShadow: '0 1px 4px rgba(0,0,0,0.9)',
            transform: `translate(${labelX * 12}px, ${-labelY * 12}px)`,
          }}
        >
          {stakeholder.label} {stakeholder.percent}%
        </div>
      </Html>
    </group>
  )
}

export function CapTableDonut3D() {
  const groupRef = useRef<THREE.Group>(null)

  useFrame((_, delta) => {
    if (groupRef.current) groupRef.current.rotation.y += delta * 0.2
  })

  const total = STAKEHOLDERS.reduce((s, d) => s + d.percent, 0)
  let cursor = 0

  return (
    <group ref={groupRef}>
      {STAKEHOLDERS.map((s, i) => {
        const startAngle = (cursor / total) * Math.PI * 2
        cursor += s.percent
        const endAngle = (cursor / total) * Math.PI * 2
        return (
          <DonutSegment
            key={s.label}
            stakeholder={s}
            startAngle={startAngle}
            endAngle={endAngle}
            index={i}
          />
        )
      })}
    </group>
  )
}
