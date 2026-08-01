import { Github } from 'lucide-react';

export default function Footer() {
  return (
    <footer className="py-12 px-6 border-t border-zinc-800 mt-20">
      <div className="max-w-7xl mx-auto flex flex-col sm:flex-row justify-between items-center gap-6">
        <div className="flex items-center gap-2 text-zinc-400">
          <span className="font-semibold text-white tracking-wide">BunkerBot</span>
          <span>&copy; {new Date().getFullYear()}</span>
        </div>
        <div className="flex items-center gap-6 text-sm text-zinc-500">
          <a href="https://github.com/PiterPentester/BunkerBot" className="hover:text-emerald-400 transition-colors flex items-center gap-2">
            <Github className="w-4 h-4" />
            PiterPentester/BunkerBot
          </a>
        </div>
      </div>
    </footer>
  );
}
