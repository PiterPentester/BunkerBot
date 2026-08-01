import { motion } from 'motion/react';
import { Users, Activity, Dna, Vote, BrainCircuit } from 'lucide-react';

const features = [
  {
    icon: Users,
    title: "Room Management",
    description: "Quick room creation with customized player capacity. Easy one-click invite links via Telegram deep-linking."
  },
  {
    icon: Activity,
    title: "Live Dashboard",
    description: "Asynchronous, concurrent state updates that dynamically edit player dashboards without spamming the chat."
  },
  {
    icon: Dna,
    title: "Rich Character Gen",
    description: "30+ Special Active Abilities, 25+ Exit Conditions, diverse professions, traits, hobbies, baggage, and secret facts."
  },
  {
    icon: Vote,
    title: "Interactive Voting",
    description: "Secret weighted voting with support for double votes, immunity shields, vote reflection, and ties."
  },
  {
    icon: BrainCircuit,
    title: "Automated Endgame",
    description: "Smart evaluation calculates survival probability based on apocalypse demands, required specialist skills, and demographics."
  }
];

export default function Features() {
  return (
    <section className="py-24 px-6 sm:px-12 max-w-7xl mx-auto">
      <div className="text-center mb-16">
        <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">Key Features</h2>
        <p className="text-zinc-400 max-w-2xl mx-auto">Everything you need to host the perfect game of Bunker right in your Telegram groups.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, delay: index * 0.1 }}
            className="p-8 rounded-2xl bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-colors"
          >
            <div className="w-12 h-12 rounded-lg bg-emerald-500/10 flex items-center justify-center mb-6">
              <feature.icon className="w-6 h-6 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">{feature.title}</h3>
            <p className="text-zinc-400 leading-relaxed">{feature.description}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
