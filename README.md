# AI Screen Reader Agent with MURF Integration

This enhanced version of the AI Screen Reader Agent integrates with MURF's high-quality text-to-speech API for superior voice output.

## 🎯 Key Features Added

- **✅ MURF API Integration**: High-quality AI voices with natural speech patterns
- **✅ Text Chunking**: Automatic handling of long texts (splits at 2800 chars)
- **✅ Sequential Audio Playback**: Seamless playback of chunked audio
- **✅ Fallback System**: Automatic fallback to pyttsx3 if MURF fails
- **✅ Configuration Support**: Easy setup with config files
- **✅ Error Handling**: Robust error handling with user feedback
- **✅ Voice Selection**: Multiple voice options and styles

## Features

- **Dual TTS Support**: Choose between MURF AI voices or local pyttsx3
- **High-Quality Voices**: Access to MURF's professional AI voices
- **Fallback System**: Automatic fallback to pyttsx3 if MURF fails
- **Voice Customization**: Select from various MURF voice options
- **Smart Audio Handling**: Efficient audio streaming and playback

## Setup

### 1. Install Dependencies

#### Option A: Automatic Installation (Recommended)
```bash
python install_dependencies.py
```

#### Option B: Manual Installation
```bash
pip install -r requirements_murf.txt
```

#### Option C: Individual Packages
```bash
pip install murf pygame requests google-generativeai
```

### 2. Get API Keys

#### Google Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Copy the key for use in the application

#### MURF API Key
1. Sign up at [MURF.ai](https://murf.ai/)
2. Navigate to your API settings
3. Generate an API key
4. Copy the key for use in the application

### 3. Configuration (Optional but Recommended)

Copy the example configuration file and customize it:

```bash
copy config_example.py config.py
```

Edit `config.py` with your API keys and preferences:

```python
# API Keys
GOOGLE_GEMINI_API_KEY = "your_actual_google_api_key"
MURF_API_KEY = "your_actual_murf_api_key"

# TTS Configuration
TTS_PROVIDER = "murf"  # or "pyttsx3"
MURF_VOICE_ID = "en-US-natalie"  # Your preferred voice
```

### 4. Run the Application

```bash
python readOut_withMURF.py
```

### 5. Test the Integration

```bash
python test_murf_integration.py
```

## Usage

### Basic Usage

```python
from readOut_withMURF import AIScreenReaderAgent

# Initialize with MURF
agent = AIScreenReaderAgent(
    google_api_key="your_google_api_key",
    murf_api_key="your_murf_api_key",
    tts_provider="murf"
)

# Initialize with pyttsx3 (fallback)
agent = AIScreenReaderAgent(
    google_api_key="your_google_api_key",
    tts_provider="pyttsx3"
)

# Run the agent
agent.run()
```

### Voice Configuration

```python
# Set MURF voice preferences
agent.user_preferences["murf_voice_id"] = "en-US-marcus"
agent.user_preferences["murf_style"] = "conversational"
```

### Available MURF Voices (Examples)

- `en-US-natalie` - Natural female voice (default)
- `en-US-marcus` - Professional male voice
- `en-US-sarah` - Friendly female voice
- `en-GB-oliver` - British male voice
- `en-AU-emma` - Australian female voice

## Keyboard Shortcuts

- **Ctrl+Shift+R**: Smart read entire screen
- **Ctrl+Shift+W**: Smart read active window
- **Ctrl+Shift+Q**: Ask question about screen
- **Ctrl+Shift+S**: Stop reading
- **Ctrl+Shift+I**: Interactive mode
- **Ctrl+Shift+X**: Quit application

## Error Handling

The application includes robust error handling:

1. **MURF API Failures**: Automatic fallback to pyttsx3
2. **Network Issues**: Graceful degradation with local TTS
3. **Audio Playback Issues**: Multiple retry mechanisms
4. **API Rate Limits**: Proper error messages and fallbacks

## 🔧 Text Chunking Feature

One of the key improvements in this integration is automatic text chunking to handle MURF's 3000-character limit:

### How It Works

1. **Automatic Detection**: The system automatically detects when text exceeds 2800 characters
2. **Smart Splitting**: Text is split at sentence boundaries to maintain natural flow
3. **Word-Level Fallback**: If sentences are too long, splitting occurs at word boundaries
4. **Sequential Playback**: Audio chunks are played seamlessly one after another
5. **User Feedback**: Clear progress indicators show chunking status

### Example Output

```
📝 Text too long (3125 chars), splitting into 2 chunks...
🎵 Processing chunk 1/2...
🎵 Processing chunk 2/2...
🔊 Playing chunk 1/2...
🔊 Playing chunk 2/2...
```

This feature ensures that even very long AI-generated content can be converted to speech without errors.

## Configuration Options

### TTS Provider Selection

```python
# Use MURF (requires API key)
tts_provider="murf"

# Use local pyttsx3
tts_provider="pyttsx3"
```

### Voice Customization

```python
# MURF voice settings
user_preferences = {
    "murf_voice_id": "en-US-natalie",
    "murf_style": "conversational"
}
```

## Troubleshooting

### Common Issues

1. **MURF API Key Invalid**
   - Verify your API key is correct
   - Check your MURF account status
   - Ensure you have sufficient credits

2. **Audio Playback Issues**
   - Install pygame: `pip install pygame`
   - Check system audio settings
   - Try fallback to pyttsx3

3. **Network Connectivity**
   - Check internet connection
   - Verify firewall settings
   - Try using pyttsx3 as fallback

### Dependencies

If you encounter import errors:

```bash
# Install missing dependencies
pip install murf pygame requests

# For Windows-specific dependencies
pip install pywin32
```

## Performance Notes

- **MURF**: Higher quality but requires internet connection
- **pyttsx3**: Lower quality but works offline
- **Audio Caching**: Consider implementing caching for repeated text
- **Rate Limits**: Be mindful of MURF API rate limits

## License

This project maintains the same license as the original AI Screen Reader Agent.
