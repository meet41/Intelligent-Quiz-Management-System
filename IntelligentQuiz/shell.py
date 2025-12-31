import os
print('Has OPENAI key:', bool(os.getenv('OPENAI_API_KEY')))
print('Provider:', os.getenv('AI_PROVIDER'))
print('Model:', os.getenv('OPENAI_MODEL', 'gpt-4o-mini'))
exit()