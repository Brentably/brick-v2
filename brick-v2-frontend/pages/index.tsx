import Image from "next/image";
import localFont from "next/font/local";
import { ChangeEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import Input from "@/components/Input";
import Loading from "@/components/Loading";
import { getEnglishTranslation } from "@/lib/getEnglishTranslation";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle } from "lucide-react";

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
        setSentenceToTranslate(data.content)
        console.log(data)
        setSentenceLoading(false)

        setEnglishTranslationPromise(getEnglishTranslation(data.content))
      })
      .catch(error => {
        console.error('Error:', error)
        setSentenceLoading(false)
      });
  }

  // this should handle allowing the user to determine whether or not they've answered correctly or not
  async function validateSentence(germanTargetSentence: string, userSentence: string, englishTranslationPromise: Promise<string>) {
    const englishTranslation = await englishTranslationPromise
    isUserValidating.current = true
    setEnglishTranslation(englishTranslation)
    console.log(`validateSentence(targetSentence: ${germanTargetSentence}, userSentence: ${userSentence}, englishTranslation: ${englishTranslation})`)

  }

  function handleValidation(isCorrect: boolean) {
    // Here you can implement logic to track user's performance if needed
    console.log(`User's translation was ${isCorrect ? 'correct' : 'incorrect'}`)
    isUserValidating.current = false
    setUserTranslation("")
    obtainAndSetSentence()
  }

  function handleSend(e: KeyboardEvent<HTMLTextAreaElement>) {
      if (englishTranslationPromise === null) throw new Error('cant handle because no english translation promise')
      setUserTranslation((e.target as HTMLTextAreaElement).value)
      validateSentence(sentenceToTranslate, (e.target as HTMLTextAreaElement).value, englishTranslationPromise)
  }

  function handleStart() {
    obtainAndSetSentence()
    setHasStarted(true)
  }


  return (
    <div
      className={`flex h-full justify-center flex-row p-10`}
    >
      {hasStarted ? 
      <div className="max-w-4x flex justify-stretch flex-col">
        <div className="text-center text-lg">

          {sentenceLoading ? <Loading /> : sentenceToTranslate}

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

      </div>

      : 
      <Button onClick={handleStart}>Push to start</Button>
      }
    </div>
  );
}
