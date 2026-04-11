import { motion } from 'framer-motion'
import { pageTransition } from '@/lib/animation-variants'
import { ReactNode } from 'react'

export function PageTransition({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={pageTransition}
      className="w-full"
    >
      {children}
    </motion.div>
  )
}
