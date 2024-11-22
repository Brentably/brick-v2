import { useState } from 'react';
import LoadingDots from './LoadingDots';

const Proficiency = () => {
  const [loading, setLoading] = useState(false);
  const [proficiency, setProficiency] = useState<string|null>(null);

  const handleLoadProficiency = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/proficiency', {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const data = await response.json();
      setProficiency(Number(data.proficiency).toFixed(4));
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-row items-center w-full justify-center mt-4">
      <button onClick={handleLoadProficiency} disabled={loading} className="mr-4">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
      </button>
      <div className="text-lg font-medium">Proficiency: </div>
      <div className="text-xl font-bold ml-2 w-6">{loading ? <LoadingDots /> : proficiency !== null ? proficiency : '?'}</div>
    </div>
  );
};

export default Proficiency;

