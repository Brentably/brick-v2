Brick v2 consistent of a NextJS frontend and a FastAPI backend.

There are several components to Brick v2, but the main idea is simple:

Learn a language by translating sentence from that language to your native language. 

Right now it's just set up for learning German from English.

The idea is simple: We can approximate language learning by simplifying it to learning individual words in context, so
the plan is to track every single word the user knows / doesn't know, and slowly introduce more words over time. 


----


The architecture:

Brick Bot v2 consists of:

- a student's learning state
  - tracking what they know and what they don't know
- a sentence generator
  - a way to generate the sentences which will yield the highest payoff to the learner based on the current learning state
- a feedback mechanism
  - how to update the learning state based on their performance in the app

These are not easy problems, and they're ones that I hope to improve on significantly over time. 

