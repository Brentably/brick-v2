export async function getEnglishTranslation(message: string, context?: string): Promise<string> {
  try {
    const response = await fetch('/api/getEnglishTranslation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, context }),
    });
    const data = await response.json();
    return data.englishTranslation;
  } catch (error) {
    console.error('Error fetching English translation:', error);
    throw new Error('Failed to fetch English translation');
  }
}