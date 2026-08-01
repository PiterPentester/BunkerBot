import { motion } from 'motion/react';
import { Github, Play, ShieldAlert } from 'lucide-react';

export default function Hero() {
  return (
    <section className="pt-32 pb-20 px-6 sm:px-12 max-w-7xl mx-auto flex flex-col items-center text-center">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="flex items-center gap-3 mb-6 px-4 py-2 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 text-sm font-medium tracking-wide"
      >
        <ShieldAlert className="w-4 h-4 text-emerald-400" />
        <span>Telegram Game Bot</span>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1, ease: "easeOut" }}
        className="text-5xl sm:text-7xl font-bold tracking-tight text-white mb-8"
      >
        Survive the <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400">Apocalypse</span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
        className="text-lg sm:text-xl text-zinc-400 max-w-2xl mb-12 leading-relaxed"
      >
        A feature-packed Telegram implementation of the popular psychological party game <strong>"Bunker"</strong>. Persuade, vote, and decide who deserves a spot in the fallout shelter to rebuild humanity.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3, ease: "easeOut" }}
        className="flex flex-col sm:flex-row items-center gap-4 w-full sm:w-auto"
      >
        <a
          href="https://github.com/PiterPentester/BunkerBot"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 bg-white text-zinc-950 font-semibold rounded-lg hover:bg-zinc-200 transition-colors"
        >
          <Github className="w-5 h-5" />
          View on GitHub
        </a>
        <a
          href="#how-to-play"
          className="flex items-center justify-center gap-2 w-full sm:w-auto px-8 py-4 bg-zinc-900 text-white font-semibold rounded-lg border border-zinc-800 hover:bg-zinc-800 transition-colors"
        >
          <Play className="w-5 h-5" />
          How to Play
        </a>
      </motion.div>
    </section>
  );
}
