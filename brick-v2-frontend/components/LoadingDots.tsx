import React from 'react';

const LoadingDots: React.FC = () => {
  const [dots, setDots] = React.useState(0);

  React.useEffect(() => {
    const intervalId = setInterval(() => {
      setDots((prevDots) => (prevDots + 1) % 4);
    }, 500);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <>
      {Array(dots).fill('.').join('')}
</>
  );
};

export default LoadingDots;

