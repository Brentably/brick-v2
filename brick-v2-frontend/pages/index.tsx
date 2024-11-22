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
  const isUserValidating = useRef<boolean>(false)

  useEffect(() => {
    const handleKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Enter' && isUserValidating.current) {
        handleValidation(true);
      } else if ((e.key === 'Backspace' || e.key === 'Delete') && isUserValidating.current) {
        handleValidation(false);
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
    const englishTranslation = await englishTranslationPromise
    isUserValidating.current = true
    setEnglishTranslation(englishTranslation)
    console.log(`validateSentence(targetSentence: ${germanTargetSentence}, userSentence: ${userSentence}, englishTranslation: ${englishTranslation})`)

  }

  function handleValidation(isCorrect: boolean) {
    // Here you can implement logic to track user's performance if needed
    console.log(`User's translation was ${isCorrect ? 'correct' : 'incorrect'}`)
    const translation = userTranslation
    setUserTranslation("")
    isUserValidating.current = false
    setSentenceLoading(true)
    fetch("http://localhost:8000/sentence_result", {
      method: "POST",
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        sentenceData: sentenceToTranslateData,
        userTranslation: translation, // b/c already set user translation to blank
        isCorrect: isCorrect
      })
    }).then(obtainAndSetSentence) // wait until data updates to get next sentence
  }

  function handleSend(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (englishTranslationPromise === null) throw new Error('cant handle because no english translation promise')
    setUserTranslation((e.target as HTMLTextAreaElement).value)
    enterValidateState(sentenceToTranslate, (e.target as HTMLTextAreaElement).value, englishTranslationPromise)
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

            <Input handleSend={handleSend} disabled={sentenceLoading} value={userTranslation} setInput={setUserTranslation} displayMode={isUserValidating.current} />

            {isUserValidating.current ?
              <>
                <div className="text-center text-md mt-4">Correct translation:</div>
                <Input disabled={true} value={englishTranslation} displayMode={true} />
                {/* <div className="text-center text-lg font-medium mt-4">{englishTranslation}</div> */}
                <div className="flex justify-center space-x-4 mt-4">
                  <Button onClick={() => handleValidation(false)} className="bg-red-500 hover:bg-red-600">
                    <XCircle className="mr-2 h-4 w-4" /> Incorrect
                  </Button>
                  <Button onClick={() => handleValidation(true)} className="bg-green-500 hover:bg-green-600">
                    <CheckCircle className="mr-2 h-4 w-4" /> Correct
                  </Button>
                </div>
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
