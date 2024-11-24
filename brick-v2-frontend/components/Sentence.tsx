import { getEnglishTranslation } from '@/lib/getEnglishTranslation';
import React, { Dispatch, SetStateAction, useState } from 'react';

interface SentenceProps {
  sentenceToTranslateData: MessageData;
  setSentenceToTranslateData: Dispatch<SetStateAction<null | MessageData>>;
}

const Sentence: React.FC<SentenceProps> = ({ sentenceToTranslateData, setSentenceToTranslateData }) => {
  const [hoveredId, setHoveredId] = useState<number | null>(null);

  const handleTokenClick = async (id: number) => {
    // Mark token as clicked and translation loading
    setSentenceToTranslateData((data) => {
      if (!data) throw new Error();
      const newData = data.data.map((token) =>
        token.id === id
          ? { ...token, isClicked: true, translationLoading: true }
          : token
      );
      return { message: data.message, data: newData, focus_words: data.focus_words };
    });

    const translation = await getTranslationForToken(id);

    // Update data with translation in context
    setSentenceToTranslateData((data) => {
      if (!data) throw new Error();
      const newData = data.data.map((token) =>
        token.id === id
          ? { ...token, isClicked: true, translationLoading: false, translationInContext: translation }
          : token
      );
      return { message: data.message, data: newData, focus_words: data.focus_words };
    });
  };

  const getTranslationForToken = async (id: number) => {
    const tokens = sentenceToTranslateData.data.filter((token) => token.id === id);
    let wordToTranslate = '';
    if (tokens.length === 1) wordToTranslate = tokens[0].token;
    if (tokens.length === 2) wordToTranslate = tokens[1].token + tokens[0].token;
    if (tokens.length > 2) {
      throw new Error(`>2 tokens with same id. id is ${id}. tokens: ${JSON.stringify(sentenceToTranslateData.data)}`);
    }
    return await getEnglishTranslation(wordToTranslate, sentenceToTranslateData.message);
  };

  const handleMouseEnter = (id: number) => {
    setHoveredId(id);
  };

  const handleMouseLeave = () => {
    setHoveredId(null);
  };

  return (
    <>
      {sentenceToTranslateData.data.map((tokenInfo: TokenInfo, index: number) => (
        <Token
          key={index}
          tokenInfo={tokenInfo}
          handleTokenClick={handleTokenClick}
          isHovered={tokenInfo.id === hoveredId && hoveredId !== null}
          onMouseEnter={() => handleMouseEnter(tokenInfo.id!)}
          onMouseLeave={handleMouseLeave}
        />
      ))}
    </>
  );
};

export default Sentence;

interface TokenProps {
  tokenInfo: TokenInfo;
  handleTokenClick: (id: number) => void;
  isHovered: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

const Token: React.FC<TokenProps> = ({ tokenInfo, handleTokenClick, isHovered, onMouseEnter, onMouseLeave }) => {
  const isGrammarToken = !tokenInfo.id;
  const baseClass = isGrammarToken ? '' : 'cursor-pointer';
  const hoverClass = isHovered ? 'bg-lime-100' : '';

  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <span
        className={`${baseClass} ${hoverClass}`}
        onClick={() => !isGrammarToken && handleTokenClick(tokenInfo.id!)}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
      >
        {tokenInfo.token}
      </span>
      {tokenInfo.token_ws === ' ' ? '\u00A0' : tokenInfo.token_ws}
      {isHovered && tokenInfo.isClicked && (
        <div className="absolute bottom-full mb-1 left-0 bg-white border rounded px-2 py-1 text-sm shadow-lg z-10">
          {tokenInfo.translationLoading
            ? 'Loading...'
            : tokenInfo.translationInContext}
        </div>
      )}
    </span>
  );
};
