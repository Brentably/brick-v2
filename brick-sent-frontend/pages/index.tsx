import Image from "next/image";
import localFont from "next/font/local";
import { ChangeEvent, KeyboardEvent, useRef, useState } from "react";
import Input from "@/components/Input";
import Loading from "@/components/Loading";

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

  function ObtainAndSetSentence() {
    setSentenceLoading(true)
    fetch('http://localhost:8000/sentence')
      .then(response => response.json())
      .then(data => {
        setSentenceToTranslate(data.content)
        console.log(data)
        setSentenceLoading(false)
      })
      .catch(error => {
        console.error('Error:', error)
        setSentenceLoading(false)
      });
  }

  function validateSentence(germanTargetSentence: string, userSentence: string) {
    console.log(`validateSentence(targetSentence: ${germanTargetSentence}, userSentence: ${userSentence})`)
  }

  function handleSend(e: KeyboardEvent<HTMLTextAreaElement>) {
    if(!hasStarted) {
      ObtainAndSetSentence()
      setHasStarted(true)
    } else {
      validateSentence(sentenceToTranslate, (e.target as HTMLTextAreaElement).value)
      
    }
  }


  return (
    <div
      className={`flex h-full justify-center flex-row p-10`}
    >
    <div className="max-w-4x flex justify-stretch flex-col">
      <div className="text-center text-lg">

        {sentenceLoading ? <Loading /> : sentenceToTranslate}

      </div>

      <Input handleSend={handleSend} disabled={sentenceLoading} />

      </div>
    </div>
  );
}
