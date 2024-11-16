import React from 'react';

const Loading: React.FC = () => {
  const [dots, setDots] = React.useState(0);

  React.useEffect(() => {
    const intervalId = setInterval(() => {
      setDots((prevDots) => (prevDots + 1) % 4);
    }, 500);
    return () => clearInterval(intervalId);
  }, []);

  return (
    <div>
      Generating sentence{Array(dots).fill('.').join('')}
    </div>
  );
};

export default Loading;

