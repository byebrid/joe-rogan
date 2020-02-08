# Joe "Joe Rogan" Rogan
For finding those Joe *"insert reference here"* Rogan comments on youtube.

The script will write these comments to a csv file called joe-rogan.csv. You can bask in their glory there.

## Requirements
* Python 3.6 or greater

## Usage
```
git clone https://github.com/byebrid/joe-rogan.git
cd joe-rogan
touch config.json
```

Now open config.json and copy-paste the following:
```
{
    "YOUTUBE_API_KEY": "<Insert your youtube API key here>"
}
```

Now you can continue (assuming linux-like system):
```
python -m venv venv
source venv/bin/activate
pip install requirements.txt
python joe-rogan.py
```

Now you simply need to let this run for as long as you'd like. This script will take many days, I think, to finish completely but you can stop it whenever you like.
