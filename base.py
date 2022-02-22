from asyncio.windows_events import NULL
from lib2to3.pgen2 import driver
from logging import exception
from numpy import full
import time
from threading import Thread
import os
from os import path
from selenium import webdriver
from selenium.webdriver import Firefox, FirefoxProfile
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
import subprocess
import speech_recognition as sr
from pydub import AudioSegment
from pydub.silence import split_on_silence
import warnings
import shutil
import librosa
import numpy as np
import glob


directory = ''
userName = ""
password = ""
geckoLoc = ""
firefoxLoc = ""
ffmpegBinLoc = ''
links = {}
r = sr.Recognizer()
start = 0.0
downloadFile = ""
title = ""
chunks = np.array([], dtype=object)
warnings.filterwarnings("ignore", category=DeprecationWarning) 


def loadValues():
    global userName, password, geckoLoc, firefoxLoc, ffmpegBinLoc, links, directory
    f = open("values.txt", "r")
    userName = str(f.readline().strip("\n"))
    password = str(f.readline().strip("\n"))
    geckoLoc = str(f.readline().strip("\n"))
    firefoxLoc = str(f.readline().strip("\n"))
    ffmpegBinLoc = str(f.readline().strip("\n"))
    directory = str(f.readline().strip("\n"))
    try:
        assert f.readline().strip("\n") == "Courses"
    except AssertionError:
        print("Error missing Keyword 'Courses' on line 6")
        print("Please add it and put your courses under")
        exit()

    #Load in courses - stop when we reach end
    while True:
        code = f.readline().strip("\n")
        if code == "END" or code == "" or code == NULL:
            print("Loaded your values successfully")
            return

        link = f.readline().strip("\n")
        links.update({code: link})
        



#print(sys.executable)
def makeAudio(path):
    
    command = 'ffmpeg -i {} -ab 160k -ar 44100 -vn audio.wav'.format(path)
    subprocess.call(command, shell=True, env={'PATH': ffmpegBinLoc})



def createChunks(path):
    """
    Splitting the large audio file into chunks
    and apply speech recognition on each of these chunks
    """
    print("Start")
    # open the audio file using pydub
    sound = AudioSegment.from_wav(path)  
    # split audio sound where silence is 700 miliseconds or more and get chunks
    chunks = split_on_silence(sound,
        # experiment with this value for your target audio file
        min_silence_len = 650,
        # adjust this per requirement
        silence_thresh = sound.dBFS-14,
        # keep the silence for 1 second, adjustable as well
        keep_silence=500,
    )
    folder_name = "audio-chunks"
    # create a directory to store the audio chunks
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    
    # process each chunk 
    count = 0
    print("Chunks split")
    for i, audio_chunk in enumerate(chunks):
        # export audio chunk and save it in
        # the `folder_name` directory.
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        audio_chunk.export(chunk_filename, format="wav")
        count += 1
    print("Chunks created")

    f = open("chunkDetails.txt", "w")
    f.write((str(count)))
    f.close()


#Process chunks - used for threaded version
def processChunksT(start, end):
    global chunks
    
    folder_name = "audio-chunks"
    for i in range(start, end):
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        if(not os.path.exists(chunk_filename)):
            print("Chunk doesn't exists")
            return
        with sr.AudioFile(chunk_filename) as source:
            audio_listened = r.record(source)
            try:
                text = r.recognize_google(audio_listened)
            except sr.UnknownValueError as e:
                print("Unknown Value: ", str(e))
            except sr.RequestError as e:
                print("Timed out")
                print("Try again ")
                exit()
            else:
                text = f"{text.capitalize()}. "
                #print(chunk_filename, ":", text)
                #outputFile.write(text + "\n")
                chunks[i] = text
                print("Chunk " + str(i))
                

def processChunks(start):
     # recognize the chunk 
    f = open("chunkDetails.txt", "r")
    last = int(f.read().strip("\n"))
    folder_name = "audio-chunks"
    whole_text = ""
    outputFile = open("transcript.txt", "a")
    print("Processing chunks. There are: " + str((last-start)))
    for i in range(start, (last)):
        chunk_filename = os.path.join(folder_name, f"chunk{i}.wav")
        with sr.AudioFile(chunk_filename) as source:
            audio_listened = r.record(source)
            # try converting it to text
            try:
                text = r.recognize_google(audio_listened)
            except sr.UnknownValueError as e:
                print("Unknown Value: ", str(e))
            except sr.RequestError as e:
                print("Timed out")
                print("Try again - finished on " + str(i))
                exit()
            else:
                text = f"{text.capitalize()}. "
                #print(chunk_filename, ":", text)
                outputFile.write(text + "\n")
                print("Chunk " + str(i))
                whole_text += text
    # return the text for all chunks detected
    outputFile.write("-----------END-------------")
    print("Complete! Check transcript.txt")
    return whole_text


def download(courseCode):
    global start, title

    start = time.time()

    opts = Options()
    profile = FirefoxProfile(firefoxLoc)

    #opts.headless = True
    global driver
    driver = webdriver.Firefox(executable_path=geckoLoc, options=opts, firefox_profile=profile)
    driver.get(links[courseCode])
    driver.find_element_by_id('adfsUrl').click()
    driver.find_element_by_id('userNameInput').send_keys(userName)
    driver.find_element_by_id('passwordInput').send_keys(password)
    driver.find_element_by_id('submitButton').click()
    print("Waiting")
    driver.maximize_window()
    time.sleep(9)

    c = driver.find_elements_by_tag_name("iframe")

    for thing in c:
        if(thing.get_attribute("src").count("vstream") > 0):
            actual = thing
            break

    driver.get(actual.get_attribute("src"))

    print("Wait second")
    time.sleep(7)
    link = driver.find_element_by_class_name("detail-title").get_attribute("href")


    driver.get(link)

    time.sleep(5)
    title = driver.find_element_by_id("deliveryTitle").get_attribute("innerHTML")
    print("Downloading:")
    print(title)
    print("----------")
    driver.find_element_by_id("podcastDownload").click()


def waitForDownload():
    global downloadFile
    time.sleep(10)
    list_of_files = glob.glob(directory + '*.mp4') 
    downloadFile = str(max(list_of_files, key=os.path.getctime))
    os.rename(downloadFile, downloadFile.replace(" ", "_"))
    downloadFile = downloadFile.replace(" ", "_")
    print("Download file is: " + downloadFile)  #comes with directory too


    #Check every 5 seconds if file downloaded
    while True:
        time.sleep(5)
        if(os.path.getsize(downloadFile) > 1000000):
            break
    print("Download finished - closing browser")
    driver.close()

def writeChunks():
    f = open("transcript.txt", "a")
    print("Begun writing")
    for c in chunks:
        f.write(str(c) + "\n")
    print("Finished writing")
    f.close()


def deleteTemps():
    if os.path.exists("audio-chunks"):
        shutil.rmtree("audio-chunks")
    else:
        pass

    if os.path.exists("audio.wav"):
        os.remove("audio.wav")
    else:
        pass

    if os.path.exists("chunkDetails.txt"):
        os.remove("chunkDetails.txt")
    else:
        pass
    print("deleted all temp files - the .mp4 of the lecture is still there")


def fullProcessOLD(courseCode):
    download(courseCode)
    waitForDownload()
    makeAudio(downloadFile)
    print(createChunks("audio.wav"))
    processChunks(0)
    end = time.time()
    os.rename("transcript.txt", title + "_transcript.txt")
    deleteTemps()
    print("Took " + str(((end-start)/60.0)))

def fullProcessThreads(courseCode):
    global chunks
    download(courseCode)
    waitForDownload()
    makeAudio(downloadFile)
    print(createChunks("audio.wav"))

    size = int(open("chunkDetails.txt", "r").read().strip("\n"))
    chunks = np.resize(chunks, size)
    threadNum = 4
    threads = []
    for i in range (0, threadNum):
        if i == threadNum-1:
            t = Thread(target=processChunksT, args=(int(i * (size/threadNum)), size))
        else:
           t = Thread( target=processChunksT, args = (int(i * (size/threadNum)), int((i * (size/threadNum)) + (size/threadNum))))
        threads.append(t)

    for x in threads:
        x.start()

    for x in threads:
        x.join()

    writeChunks()
    end = time.time()
    os.rename("transcript.txt", title + "_transcript.txt")
    deleteTemps()
    print("Took " + str(((end-start)/60.0)) + " minutes")




def resumeFromCutOLD(cutoff):
    processChunks(cutoff)
    os.rename("transcript.txt", title + "_transcript.txt")
    deleteTemps()


#print(str(librosa.get_duration(filename="Welcome_to_SWEN301_2022_default.mp4")))

loadValues()
valid = False
while not valid:
    print("Welcome what would you like to do?")
    print("Type a code to download and transcribe")
    #print("Type 'resume' if your last process got cut off")
    option = str(input("Option: "))

    # if(option == "resume"):
    #     num = int(input("Where did it fail? "))
    #     valid = True
    #     resumeFromCut(num)
    # else:
    if(option in links):
        valid = True
        fullProcessThreads(option)
    else:
        print("Invalid - check spelling and codes in values.txt")


print("Exiting")
exit()