import { useRef, useMemo } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

interface AmbientParticlesProps {
  count?: number
  color?: string
  spread?: number
}

export function AmbientParticles({ count = 60, color = '#6366f1', spread = 10 }: AmbientParticlesProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null)

  const positions = useMemo(() => {
    const pos = new Float32Array(count * 3)
    for (let i = 0; i < count; i++) {
      pos[i * 3] = (Math.random() - 0.5) * spread
      pos[i * 3 + 1] = (Math.random() - 0.5) * spread
      pos[i * 3 + 2] = (Math.random() - 0.5) * spread
    }
    return pos
  }, [count, spread])

  const dummy = useMemo(() => new THREE.Object3D(), [])

  useFrame(({ clock }) => {
    if (!meshRef.current) return
    const t = clock.elapsedTime * 0.1
    for (let i = 0; i < count; i++) {
      const x = positions[i * 3] + Math.sin(t + i * 0.5) * 0.3
      const y = positions[i * 3 + 1] + Math.cos(t + i * 0.3) * 0.2
      const z = positions[i * 3 + 2] + Math.sin(t + i * 0.7) * 0.1
      dummy.position.set(x, y, z)
      dummy.updateMatrix()
      meshRef.current.setMatrixAt(i, dummy.matrix)
    }
    meshRef.current.instanceMatrix.needsUpdate = true
  })

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, count]}>
      <sphereGeometry args={[0.01, 6, 6]} />
      <meshBasicMaterial color={color} transparent opacity={0.4} />
    </instancedMesh>
  )
}
