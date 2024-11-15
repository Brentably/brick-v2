import React, { useState } from 'react';

interface InputProps {
  handleSend: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  disabled?: boolean;
}

const Input: React.FC<InputProps> = ({ handleSend, disabled }) => {
  const textareaRef = React.useRef<HTMLTextAreaElement | null>(null);
  const textareaContainerRef = React.useRef<HTMLDivElement | null>(null);
  const [input, setInput] = useState('')

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (textareaRef.current === null || textareaContainerRef.current === null || disabled) return;
    textareaRef.current.style.height = "auto";
    textareaRef.current.style.height = textareaRef.current.scrollHeight + "px";
    setInput(e.target.value) // Assuming setInput is a function that updates the input state
  };

  return (
    <div ref={textareaContainerRef} className='relative flex flex-grow items-end mt-4'>
      <textarea ref={textareaRef}
        onChange={handleInputChange}
        value={input}
        rows={1}
        className='text-base chatbot-input flex-1 outline-none rounded-md p-2 resize-none m-0 w-full overflow-hidden md:min-w-96'
        placeholder='Enter your translation'
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && input.trim() !== '' && !disabled) {
            e.preventDefault();
            handleSend(e)
            setInput('')
          }
        }}
        style={{ height: '2.5rem' }}
        disabled={disabled}
      />
    </div>
  );
};

export default Input;