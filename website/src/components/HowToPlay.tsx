import { motion } from 'motion/react';
import { MessageCircle, Settings2, UserPlus, PlayCircle, Trophy } from 'lucide-react';

const steps = [
  {
    icon: MessageCircle,
    title: "1. Start the Bot",
    description: "Send /start to the bot on Telegram to initialize your session."
  },
  {
    icon: Settings2,
    title: "2. Create a Game",
    description: "Click \"Створити гру 🎲\" and set the total players and available bunker seats."
  },
  {
    icon: UserPlus,
    title: "3. Invite Friends",
    description: "Share the generated deep-link invite with your group to let them join the lobby."
  },
  {
    icon: PlayCircle,
    title: "4. Game Loop",
    description: "Reveal your characteristics to persuade others. Use special action cards to turn the tables, and vote on who gets exiled."
  },
  {
    icon: Trophy,
    title: "5. Final Evaluation",
    description: "Once the remaining players fit inside the bunker, the system automatically evaluates if humanity survives!"
  }
];

export default function HowToPlay() {
  return (
    <section id="how-to-play" className="py-24 px-6 sm:px-12 max-w-7xl mx-auto bg-zinc-900/50 rounded-3xl border border-zinc-800/50 my-12">
      <div className="text-center mb-16">
        <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">How to Play</h2>
        <p className="text-zinc-400 max-w-2xl mx-auto">Get your group ready and dive into the apocalypse in five simple steps.</p>
      </div>

      <div className="flex flex-col space-y-8 max-w-3xl mx-auto relative">
        <div className="absolute left-[27px] top-4 bottom-4 w-px bg-zinc-800 hidden sm:block"></div>
        
        {steps.map((step, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="flex flex-col sm:flex-row gap-6 relative"
          >
            <div className="flex-shrink-0 w-14 h-14 rounded-full bg-zinc-950 border-2 border-zinc-800 flex items-center justify-center z-10 relative">
              <step.icon className="w-6 h-6 text-emerald-400" />
            </div>
            <div className="pt-3 sm:pt-4">
              <h3 className="text-xl font-bold text-white mb-2">{step.title}</h3>
              <p className="text-zinc-400 leading-relaxed">{step.description}</p>
            </div>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
