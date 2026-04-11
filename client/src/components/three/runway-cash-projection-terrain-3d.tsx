import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { OrbitControls, Grid } from '@react-three/drei'

interface RunwayTerrainProps {
  data?: { month: number; cash: number; burnRate: number }[]
}

function generateSampleData(): { month: number; cash: number; burnRate: number }[] {
  const data = []
  let cash = 50000
  const burnRate = 2000
  for (let m = 0; m < 25; m++) {
    data.push({ month: m, cash, burnRate })
    cash = Math.max(0, cash - burnRate + Math.random() * 1000 - 500)
  }
  return data
}

export function RunwayTerrain({ data }: RunwayTerrainProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const baseYRef = useRef<Float32Array | null>(null)
  const terrainData = useMemo(() => data ?? generateSampleData(), [data])

  const { geometry } = useMemo(() => {
    const width = 6
    const depth = 4
    const segX = terrainData.length - 1
    const segZ = 10
    const geo = new THREE.PlaneGeometry(width, depth, segX, segZ)
    geo.rotateX(-Math.PI / 2)

    const positions = geo.attributes.position
    const colorArray = new Float32Array(positions.count * 3)
    const maxCash = Math.max(...terrainData.map(d => d.cash))

    for (let i = 0; i < positions.count; i++) {
      const x = positions.getX(i)
      const z = positions.getZ(i)

      const dataIdx = Math.round(((x + width / 2) / width) * (terrainData.length - 1))
      const clampedIdx = Math.max(0, Math.min(terrainData.length - 1, dataIdx))
      const point = terrainData[clampedIdx]

      const noise = (Math.random() - 0.5) * 0.3 * Math.abs(z)
      const height = (point.cash / maxCash) * 2 + noise
      positions.setY(i, Math.max(0, height))

      const normalizedH = Math.max(0, height) / 2.5
      if (normalizedH > 0.6) {
        // Green - safe
        colorArray[i * 3] = 0.13
        colorArray[i * 3 + 1] = 0.77
        colorArray[i * 3 + 2] = 0.36
      } else if (normalizedH > 0.3) {
        // Amber - caution
        colorArray[i * 3] = 0.96
        colorArray[i * 3 + 1] = 0.62
        colorArray[i * 3 + 2] = 0.04
      } else {
        // Red - danger
        colorArray[i * 3] = 0.94
        colorArray[i * 3 + 1] = 0.27
        colorArray[i * 3 + 2] = 0.27
      }
    }

    geo.computeVertexNormals()
    geo.setAttribute('color', new THREE.BufferAttribute(colorArray, 3))

    // Snapshot base Y values for wave animation
    const ySnapshot = new Float32Array(positions.count)
    for (let i = 0; i < positions.count; i++) {
      ySnapshot[i] = positions.getY(i)
    }
    baseYRef.current = ySnapshot

    return { geometry: geo }
  }, [terrainData])

  useFrame(({ clock }) => {
    if (!meshRef.current || !baseYRef.current) return
    const positions = meshRef.current.geometry.attributes.position
    const time = clock.elapsedTime * 0.5
    for (let i = 0; i < positions.count; i++) {
      const baseY = baseYRef.current[i]
      const wave = Math.sin(time + positions.getX(i) * 2) * 0.02
      positions.setY(i, baseY + wave)
    }
    positions.needsUpdate = true
  })

  return (
    <group>
      <mesh ref={meshRef} geometry={geometry}>
        <meshStandardMaterial
          vertexColors
          transparent
          opacity={0.85}
          side={THREE.DoubleSide}
          wireframe={false}
        />
      </mesh>

      {/* Wireframe overlay */}
      <mesh geometry={geometry}>
        <meshBasicMaterial
          color="#ffffff"
          transparent
          opacity={0.05}
          wireframe
        />
      </mesh>

      <OrbitControls
        enableZoom={true}
        enablePan={false}
        maxPolarAngle={Math.PI / 2.2}
        minDistance={3}
        maxDistance={10}
        autoRotate
        autoRotateSpeed={0.5}
      />

      <Grid
        args={[10, 10]}
        position={[0, -0.01, 0]}
        cellSize={0.5}
        cellColor="#ffffff"
        sectionSize={2}
        sectionColor="#6366f1"
        fadeDistance={15}
        cellThickness={0.3}
        sectionThickness={0.6}
        infiniteGrid
      />
    </group>
  )
}
