import { useEffect, useRef } from 'react'
import { createNoise3D } from 'simplex-noise'

interface Props {
  className?: string
  /** base step speed in px/frame — low for a slow, ambient drift */
  speed?: number
  /** particle density multiplier */
  density?: number
  /** trail fade alpha per frame (higher = crisper dots / shorter trails) */
  fade?: number
  /** render a single still field instead of animating */
  staticMode?: boolean
}

interface P {
  x: number
  y: number
  life: number
  alpha: number
  size: number
}

// Flow-field constants (tuned against the reference by offline render checks).
const SCALE = 0.0015 // noise frequency → curve size (smaller = bigger sweeps)
const TSTEP = 0.0007 // how fast the field morphs
const PER = 130 // 1 dot per ~130 px²
const CAP = 7000 // max dots (perf ceiling)

/**
 * Fluid-particles background: thousands of small dots drift along a slowly
 * evolving 3D-simplex-noise flow field over pure black. The dots bunch along
 * the field's streamlines, tracing large sweeping curved bands — matching the
 * reference. Each dot leaves a short fading trail. Honors prefers-reduced-motion.
 */
export default function FluidParticles({
  className,
  speed = 0.45,
  density = 1,
  fade = 0.16,
  staticMode = false,
}: Props) {
  const ref = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = ref.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const noise = createNoise3D()
    let w = 0
    let h = 0
    let particles: P[] = []
    let t = 0
    let raf = 0

    const spawn = (): P => {
      const r = Math.random()
      return {
        x: Math.random() * w,
        y: Math.random() * h,
        life: 60 + Math.random() * 300,
        // mostly dim grain, a moderate tier, a few bright dots for depth
        alpha: r > 0.88 ? 0.95 : r > 0.5 ? 0.6 : 0.34,
        size: r > 0.92 ? 1.6 : 1,
      }
    }

    const resize = () => {
      const parent = canvas.parentElement
      w = parent ? parent.clientWidth : window.innerWidth
      h = parent ? parent.clientHeight : window.innerHeight
      canvas.width = Math.floor(w * dpr)
      canvas.height = Math.floor(h * dpr)
      canvas.style.width = `${w}px`
      canvas.style.height = `${h}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      ctx.fillStyle = '#000'
      ctx.fillRect(0, 0, w, h)
      const count = Math.min(CAP, Math.max(400, Math.floor(((w * h) / PER) * density)))
      particles = Array.from({ length: count }, spawn)
    }

    const step = () => {
      ctx.fillStyle = `rgba(0,0,0,${fade})` // fade prior frame → short dotted trails
      ctx.fillRect(0, 0, w, h)
      ctx.fillStyle = '#ffffff'
      for (const p of particles) {
        const a = noise(p.x * SCALE, p.y * SCALE, t) * Math.PI * 2
        p.x += Math.cos(a) * speed
        p.y += Math.sin(a) * speed
        p.life -= 1
        if (p.life <= 0 || p.x < -8 || p.x > w + 8 || p.y < -8 || p.y > h + 8) {
          Object.assign(p, spawn())
          continue
        }
        ctx.globalAlpha = p.alpha
        ctx.fillRect(p.x, p.y, p.size, p.size)
      }
      ctx.globalAlpha = 1
      t += TSTEP
    }

    resize()
    if (reduce || staticMode) {
      for (let i = 0; i < 420; i++) step()
    } else {
      const loop = () => {
        step()
        raf = requestAnimationFrame(loop)
      }
      raf = requestAnimationFrame(loop)
    }

    const onResize = () => resize()
    window.addEventListener('resize', onResize)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', onResize)
    }
  }, [speed, density, fade, staticMode])

  return <canvas ref={ref} className={`pointer-events-none absolute inset-0 ${className ?? ''}`} />
}
