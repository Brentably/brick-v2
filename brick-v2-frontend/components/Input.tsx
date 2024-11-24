import React, { useEffect } from 'react';

interface InputProps {
  handleSend?: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  disabled?: boolean;
  value: string;
  setInput?: (input: string) => void;
  displayMode?: boolean; // New prop for display mode
}

const Input: React.FC<InputProps> = ({ handleSend, disabled, value, setInput, displayMode = false }) => {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const textareaContainerRef = React.useRef<HTMLDivElement | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (textareaRef.current === null || textareaContainerRef.current === null || disabled || displayMode) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    setInput?.(e.target.value)
  };

  useEffect(() => {
    if (!displayMode && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [displayMode, disabled]);

  return (
    <div ref={textareaContainerRef} className='relative flex flex-grow items-end mt-4'>
      <textarea
        ref={textareaRef}
        onChange={handleInputChange}
        value={value}
        rows={1}
        className={`text-base chatbot-input flex-1 outline-none rounded-md p-2 resize-none m-0 w-full overflow-hidden md:min-w-96 ${displayMode ? 'bg-gray-100 cursor-default' : ''}`}
        placeholder='Enter your translation'
        style={{ height: '2.5rem' }}
        disabled={disabled || displayMode}
        readOnly={displayMode}
      />
    </div>
  );
};

export default Input;