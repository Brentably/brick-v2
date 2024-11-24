import Image from "next/image";
import localFont from "next/font/local";
import { ChangeEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import Input from "@/components/Input";
import LoadingDots from "@/components/LoadingDots";
import { getEnglishTranslation } from "@/lib/getEnglishTranslation";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle } from "lucide-react";
import bricks from "../public/assets/bricks.svg"
import Sentence from "@/components/Sentence";
import Proficiency from "@/components/Proficiency";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export default function Home() {
  const [sentenceToTranslate, setSentenceToTranslate] = useState<string>("type anything and hit enter to start")
  const [sentenceToTranslateData, setSentenceToTranslateData] = useState<null | MessageData>(null)
  const [hasStarted, setHasStarted] = useState<boolean>(false)
  const [sentenceLoading, setSentenceLoading] = useState(false)
  const [englishTranslationPromise, setEnglishTranslationPromise] = useState<Promise<string> | null>(null)
  const [englishTranslation, setEnglishTranslation] = useState<string>("")
  const [userTranslation, setUserTranslation] = useState<string>("")
  const [wordValidations, setWordValidations] = useState<Record<string, boolean>>({});
  const isUserValidating = useRef<boolean>(false)

function handleKey(isEnter: boolean) {
  console.log('handleKey() called')
  // if sentence is loading, then do nothing
  // if user is not validating, and sentence is not loading, then handleSend
  // if user is validating, then mark incorrect / correct things
  if(sentenceLoading) return  

  if (isUserValidating.current === false && userTranslation.trim() !== '' && isEnter) {
    handleSend(userTranslation)
  } else if (isUserValidating.current === true && Object.keys(wordValidations).length === sentenceToTranslateData?.focus_words.length && isEnter) {
    handleValidation()
  } else if (isUserValidating.current === true) {
    // find the next unvalidated word and mark it as correct / incorrect
    const nextUnvalidatedWord = sentenceToTranslateData?.focus_words.find(word => !(word in wordValidations));
    if (nextUnvalidatedWord) {
        setWordValidations(prev => ({
          ...prev,
          [nextUnvalidatedWord]: isEnter
        }));
      }
    } else {
      console.log('no unvalidated words')
    }
  }


  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleKey(true)
      } else if ((e.key === 'Backspace' || e.key === 'Delete')) {
        handleKey(false)
      }
    };
    document.body.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleValidation]);

  async function obtainAndSetSentence() {
    console.log('oASS() called')
    setSentenceLoading(true)
    fetch('http://localhost:8000/sentence')
      .then(response => response.json())
      .then(data => {
        console.log('data:\n')
        console.log(data)

        setSentenceToTranslateData(data)
        setSentenceToTranslate(data.message)
        setSentenceLoading(false)

        setEnglishTranslationPromise(getEnglishTranslation(data.message))
      })
      .catch(error => {
        console.error('Error:', error)
        setSentenceLoading(false)
      });
  }

  // this should handle allowing the user to determine whether or not they've answered correctly or not
  async function enterValidateState(germanTargetSentence: string, userSentence: string, englishTranslationPromise: Promise<string>) {
    const englishTranslation = await englishTranslationPromise;
    isUserValidating.current = true;
    setEnglishTranslation(englishTranslation);
    
    setWordValidations({})

    console.log(`validateSentence(targetSentence: ${germanTargetSentence}, userSentence: ${userSentence}, englishTranslation: ${englishTranslation})`)
  }

  // 
  function handleValidation() {
    if (sentenceToTranslateData === null) throw new Error('Cannot handle validation because sentenceToTranslateData is null');
    
    console.log(`User's word validations:`, wordValidations);
    const translation = userTranslation;
    setUserTranslation("");
    isUserValidating.current = false;
    setSentenceLoading(true);
    
    fetch("http://localhost:8000/sentence_result", {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sentenceData: sentenceToTranslateData,
        englishTranslation: englishTranslation,
        userTranslation: translation,
        wordValidations: wordValidations, // Include per-word validations
        focus_words: sentenceToTranslateData.focus_words
      })
    }).then(obtainAndSetSentence).catch(error => {
      console.error('Error:', error);
      setSentenceLoading(false);
    });
  }

  function handleSend(userTranslation: string) {
    if (englishTranslationPromise === null) throw new Error('Cannot handle because no english translation promise')
    setUserTranslation(userTranslation)
    enterValidateState(sentenceToTranslate, userTranslation, englishTranslationPromise)
  }

  function handleStart() {
    obtainAndSetSentence()
    setHasStarted(true)
  }


  return (
    <div
      className={`flex h-full justify-center flex-row p-10`}
    >
      <div className="flex flex-col items-center">
        <div className='flex items-center gap-2 mb-10'>
          <Image src={bricks} alt='' className='w-10' />
          <div className='flex items-center'>
            <h1 className='chatbot-text-primary text-xl lg:text-3xl font-medium'>Brick Bot v2</h1>
            {/* <span className='ml-2 bg-[var(--background-soft)] text-[var(--text-primary-main)] px-2 py-1 text-xs rounded'>Beta</span> */}
          </div>
        </div>

        {hasStarted ?
          <div className="max-w-4x flex justify-stretch flex-col">
            <div className="text-center text-lg">

              {sentenceLoading || (sentenceToTranslateData === null) ?
                <div>Generating Sentence<LoadingDots /></div> :
                <Sentence sentenceToTranslateData={sentenceToTranslateData!} setSentenceToTranslateData={setSentenceToTranslateData} />}

            </div>

            <Input disabled={sentenceLoading} value={userTranslation} setInput={setUserTranslation} displayMode={isUserValidating.current} />

            {isUserValidating.current ?
              <>
                <div className="text-center text-md mt-4">Correct translation:</div>
                <Input disabled={true} value={englishTranslation} displayMode={true} />
                
                <div className="mt-4">
                  {sentenceToTranslateData?.focus_words.map(word => (
                    <div key={word} className="flex items-center mb-2">
                      <span className="w-24 mr-2">{word}</span>
                      <Button
                        onClick={() => setWordValidations(prev => ({
                          ...prev,
                          [word]: true
                        }))}
                        className={`w-32 justify-center mr-2 ${
                          wordValidations?.[word] === true 
                            ? 'bg-green-700' 
                            : 'bg-green-100 hover:bg-green-200 text-green-700'
                        }`}
                      >
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Correct
                      </Button>
                      <Button
                        onClick={() => setWordValidations(prev => ({
                          ...prev,
                          [word]: false
                        }))}
                        className={`w-32 justify-center ${
                          wordValidations?.[word] === false
                            ? 'bg-red-700'
                            : 'bg-red-100 hover:bg-red-200 text-red-700'
                        }`}
                      >
                        <XCircle className="mr-2 h-4 w-4" />
                        Incorrect
                      </Button>
                    </div>
                  ))}
                </div>
                
                <Button 
                  onClick={handleValidation} 
                  className="mt-4"
                  disabled={Object.keys(wordValidations).length !== sentenceToTranslateData?.focus_words.length}
                >
                  Submit Validation
                </Button>
                
                <div className="mt-4 text-sm text-center">
                  (As long as it's roughly correct, that's ok. That is: the meaning is conveyed.)
                </div>
              </>
              : null
            }
            <Proficiency/>
          </div>

          :
          <Button onClick={handleStart}>Push to start</Button>
        }
      </div>
    </div>
  );

}

