import Hero from './components/Hero';
import Features from './components/Features';
import Terminal from './components/Terminal';
import HowToPlay from './components/HowToPlay';
import Footer from './components/Footer';

export default function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-50 selection:bg-emerald-500/30 selection:text-emerald-200">
      <main>
        <Hero />
        <Features />
        <Terminal />
        <HowToPlay />
      </main>
      <Footer />
    </div>
  );
}
