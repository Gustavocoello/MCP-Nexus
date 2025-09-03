import { useNavigate } from "react-router-dom";
import useCurrentUser from '../features/auth/components/context/useCurrentUser';

function LandingPage() {
  const { user, loading } = useCurrentUser();
  const navigate = useNavigate();

  const goToChat = () => {
    if (user?.id) {
      navigate(`/c/${user.id}`);
    } else {
      navigate('/chat');
    }
  };

  const goToJarvis = () => {
    navigate('/jarvis'); // asumiendo no requiere login
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-black text-white px-6">
      <h1 className="text-5xl font-bold mb-6 text-center">Bienvenido a mi IA</h1>
      <p className="text-lg mb-12 text-gray-400 text-center">Elige tu experiencia</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <button
          onClick={goToChat}
          className="p-8 rounded-2xl border border-gray-700 bg-gray-900 hover:bg-gray-800 transition text-center shadow-lg"
        >
          <h2 className="text-2xl font-semibold mb-2">💬 Chat IA</h2>
          <p className="text-gray-400">Conversa con un asistente estilo ChatGPT.</p>
        </button>

        <button
          onClick={goToJarvis}
          className="p-8 rounded-2xl border border-gray-700 bg-gray-900 hover:bg-gray-800 transition text-center shadow-lg"
        >
          <h2 className="text-2xl font-semibold mb-2">🪐 Jarvis IA</h2>
          <p className="text-gray-400">Explora la esfera futurista de inteligencia artificial.</p>
        </button>
      </div>
    </div>
  );
}
export default LandingPage
