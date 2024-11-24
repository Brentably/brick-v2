import * as deepl from "deepl-node";
import type { NextApiRequest, NextApiResponse } from "next";

type Data = {
  englishTranslation?: string;
  error?: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<Data>
) {
  try {
    const translator = new deepl.Translator(process.env.NEXT_SERVER_DEEPL_KEY!);
    console.log("getEnglish translation hit");
    
    const { message, context } = req.body;

    console.log("translating ", message, " to english");

    const result = await translator.translateText(message, null, "en-US", {context});

    // console.log("result:");
    // console.log(result);

    res.status(200).json({
      englishTranslation: Array.isArray(result) ? result[0].text : result.text,
    });
  } catch (e) {
    console.log('catch:')
    console.log(e)
    res.status(500).json({ error: "Internal Server Error" });
  }
}
