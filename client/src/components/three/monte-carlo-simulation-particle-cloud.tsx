import { useRef, useMemo, useEffect } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { OrbitControls } from '@react-three/drei'

interface SimResult {
  endCash: number
  endRunway: number
  survived: boolean
}

interface MonteCarloCloudProps {
  results?: SimResult[]
}

function generateSampleResults(n = 500): SimResult[] {
  const out: SimResult[] = []
  for (let i = 0; i < n; i++) {
    const survived = Math.random() > 0.35
    out.push({
      endCash: survived ? Math.random() * 800000 + 50000 : Math.random() * 40000,
      endRunway: survived ? Math.random() * 18 + 6 : Math.random() * 5,
      survived,
    })
  }
  return out
}

const GREEN = new THREE.Color('#22c55e')
const RED = new THREE.Color('#ef4444')

export function MonteCarloCloud({ results }: MonteCarloCloudProps) {
  const groupRef = useRef<THREE.Group>(null)
  const meshRef = useRef<THREE.InstancedMesh>(null)

  const data = useMemo(() => results ?? generateSampleResults(500), [results])

  const { positions, colors, count } = useMemo(() => {
    const maxCash = Math.max(...data.map(d => d.endCash))
    const maxRunway = Math.max(...data.map(d => d.endRunway))

    const positions: [number, number, number][] = []
    const colors: THREE.Color[] = []

    for (const r of data) {
      const x = (r.endCash / maxCash) * 4 - 2
      const y = (r.endRunway / maxRunway) * 3 - 1.5
      const z = Math.random() * 2 - 1
      positions.push([x, y, z])
      colors.push(r.survived ? GREEN.clone() : RED.clone())
    }
    return { positions, colors, count: positions.length }
  }, [data])

  const geometry = useMemo(() => new THREE.SphereGeometry(0.03, 6, 6), [])
  const material = useMemo(() => new THREE.MeshBasicMaterial({ vertexColors: true }), [])
  const dummy = useMemo(() => new THREE.Object3D(), [])

  // Write instance matrices and colors after mesh mounts
  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh) return
    positions.forEach(([x, y, z], i) => {
      dummy.position.set(x, y, z)
      dummy.updateMatrix()
      mesh.setMatrixAt(i, dummy.matrix)
      mesh.setColorAt(i, colors[i])
    })
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [positions, colors, dummy])

  useFrame((_, delta) => {
    if (groupRef.current) groupRef.current.rotation.y += delta * 0.15
  })

  return (
    <group ref={groupRef}>
      <instancedMesh ref={meshRef} args={[geometry, material, count]} />

      {/* Bounding box wireframe */}
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(4.4, 3.4, 2.4)]} />
        <lineBasicMaterial color="#ffffff" transparent opacity={0.08} />
      </lineSegments>

      <OrbitControls
        enableZoom
        enablePan={false}
        autoRotate={false}
        minDistance={3}
        maxDistance={12}
      />
    </group>
  )
}
