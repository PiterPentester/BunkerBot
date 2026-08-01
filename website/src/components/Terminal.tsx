import { motion } from 'motion/react';
import { TerminalSquare, Copy, Check } from 'lucide-react';
import { useState } from 'react';

const codeBlock = `git clone https://github.com/PiterPentester/BunkerBot.git
cd BunkerBot
uv sync
echo "TG_API_TOKEN=your_telegram_bot_token" > .env
uv run bunker_bot.py`;

export default function Terminal() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(codeBlock);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="py-24 px-6 sm:px-12 max-w-5xl mx-auto">
      <div className="flex flex-col md:flex-row gap-12 items-center">
        <div className="flex-1 space-y-6">
          <h2 className="text-3xl sm:text-4xl font-bold text-white">Fast Setup with uv</h2>
          <p className="text-zinc-400 leading-relaxed text-lg">
            BunkerBot leverages <strong>Aiogram 3</strong> for high-performance asynchronous Telegram interactions, and is managed via <strong>uv</strong> for lightning-fast dependency resolution.
          </p>
          <div className="flex flex-wrap gap-3">
            <span className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-300 text-sm font-medium">Python 3.10+</span>
            <span className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-300 text-sm font-medium">Aiogram 3.x</span>
            <span className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-300 text-sm font-medium">uv</span>
            <span className="px-3 py-1 rounded-full bg-zinc-900 border border-zinc-800 text-zinc-300 text-sm font-medium">asyncio</span>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex-1 w-full rounded-xl overflow-hidden border border-zinc-800 bg-[#0d1117] shadow-2xl"
        >
          <div className="flex items-center justify-between px-4 py-3 bg-[#161b22] border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <TerminalSquare className="w-4 h-4 text-zinc-400" />
              <span className="text-xs font-mono text-zinc-400">quickstart.sh</span>
            </div>
            <button
              onClick={handleCopy}
              className="text-zinc-400 hover:text-white transition-colors p-1"
              title="Copy code"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <div className="p-4 overflow-x-auto">
            <pre className="text-sm font-mono text-zinc-300 leading-relaxed">
              <code>{codeBlock}</code>
            </pre>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
