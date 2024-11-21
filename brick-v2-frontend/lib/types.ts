interface TokenInfo {
  token: string;
  token_ws: string;
  id?: number;
  root_words: string[];
  is_svp: boolean;
  full_svp_word?: string
  isClicked?: boolean
  translationLoading?: boolean
  translationInContext?: string
  
}

interface MessageData {
  message: string;
  data: TokenInfo[];
}
