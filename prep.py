import os
from langchain_openai import ChatOpenAI
import json
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from langchain.chains.llm import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from scrap.utils import read_text_files_from_folder,read_json
from langchain_google_genai import ChatGoogleGenerativeAI
from tqdm import tqdm
from scrap.utils import scrape_and_save,parse_xml_tree,array_to_json
import pandas as pd
import re
import csv
os.environ["GOOGLE_API_KEY"]=""
os.environ['OPENAI_API_KEY']=""
class MultiChain:
	def __init__(self):
		self.summary_prompt_template= """
		You'r legal expert given task to summarize regulations in detail. 
		#IMPORTANT- Also make sure you summarize in detail and output single paragraph.
		"{text}"
		DETAILED SUMMARY:"""

		self.qa_prompt_template="""
		You'r legal expert in {title} regulation, given task to generate question and answers from given regulation text.

		FEW SHOT EXAMPLES-
		Q: What is the {title} about in the context of Canadian law?
		A: 
		Q: Which Canadian authority or department issued the {title}?
		A: 
        Q: When was the {title} issued or enacted in Canada?
        A: 
        Q: What are the key definitions provided in the {title} according to Canadian law?
        A: 
        Q: What are the main provisions or sections outlined in the {title} under Canadian law?
        A: 
        Q: How does the {title} impact relevant subjects or stakeholders in Canada?
        A: 
        Q: Are there any specific criteria or requirements mentioned in the {title} as per Canadian law?
        A:
        Q: Does the {title} include any procedures or methods to be followed under Canadian law?
        A: 
        Q: Are there any penalties or consequences mentioned for non-compliance with the {title} according to Canadian law?
        A: 
        Q: Is there any process for review or amendment mentioned in the {title} under Canadian law?
        A: 
        Q: What is the overall purpose or objective of the {title} within the Canadian legal framework
        A: 
        
		{summary}
		#IMPORTANT- Make sure you follow FEW SHOT EXAMPLES and generate more relevant questions and answers releated to {title} regulation if necessary.


		QUESTION ANSWER:"""

		# self.llm=ChatOpenAI(temperature=0, model_name="gpt-4o")

		self.llm=ChatGoogleGenerativeAI(temperature=0,model="gemini-1.5-flash")

		self.llm_summ=ChatGoogleGenerativeAI(temperature=0.5,model="gemini-1.5-flash")


	def summary(self):
		chain={"text": RunnablePassthrough()} |PromptTemplate.from_template(self.summary_prompt_template)|self.llm_summ
		return chain


	def qa(self):
		summary=self.summary()
		chain={"title": RunnablePassthrough() , "summary": RunnablePassthrough()}|PromptTemplate.from_template(self.qa_prompt_template)|self.llm 
		return chain

	def output(self,input_text,title):
		return self._qa().invoke(title=title,text=input_text)






def summary_func():

	"""
	This function reads raw file from folder and writes its detailled summaray files into folder.
	"""
	mc=MultiChain()
	meta_data=read_json("data/laws.json")
	n=len(meta_data)
	for i in tqdm(range(n)):
		dire="data/text_summary/"
		file_name=meta_data[i]['UniqueId']+".txt"
		if os.path.exists(dire+file_name):
			print(file_name," exits in memory")
			continue
		else:
			try:
				text_f=read_text_files_from_folder("data/text_raw/"+meta_data[i]['UniqueId']+'.txt')
				output_txt=mc.summary().invoke({"text":text_f}).content
				with open("data/text_summary/{}.txt".format(meta_data[i]['UniqueId']), 'w') as f:
					f.write(output_txt)
			except Exception as e:
				print("An error occurred for UniqueId {}: {}".format(meta_data[i]['UniqueId'], e))


def qa_func():

	""" 
	This function reads summary from folder and return detailled QA pair into separate files into folder.
	"""
	mc=MultiChain()
	meta_data=read_json("data/laws.json")
	n=len(meta_data)
	for i in tqdm(range(n)):
		dire="data/text_qa/"
		file_name=meta_data[i]['UniqueId']+".txt"
		if os.path.exists(dire+file_name):
			print(file_name," exits in memory")
			continue
		else:
			try:
				text_f=read_text_files_from_folder("data/text_summary/"+meta_data[i]['UniqueId']+'.txt')
				output_txt=mc.qa().invoke({"title":meta_data[i]['title'],"summary":text_f}).content
				with open("data/text_qa/{}.txt".format(meta_data[i]['UniqueId']), 'w') as f:
					f.write(output_txt)
			except Exception as e:
				print("An error occurred for UniqueId {}: {}".format(meta_data[i]['UniqueId'], e))




def count_files_in_folder(folder_path):
    count = 0
    for _, _, files in os.walk(folder_path):
        count += len(files)
    return count

def remove_empty_text_files(folder_path):

	""" This function delete and return empty files from folder """
	for root, _, files in os.walk(folder_path):
		for file in files:
			if file.endswith(".txt"):
				file_path = os.path.join(root, file)
				if os.path.getsize(file_path) <=5:
					os.remove(file_path)
					print(f"Removed empty text file: {file_path}")

def format_qa_to_csv():

	""" format TEXT files into consildated text files"""

	directory = "data/text_qa/"
	questions = []
	answers = []
	qa_list = []

	#loop through all files
	for filename in os.listdir(directory):
		if filename.endswith(".txt"):
			with open(os.path.join(directory, filename), 'r', encoding='utf-8') as file:
				content = file.read()
				qa_pattern = re.compile(r'\*\*Q: (.*?)\*\*\n\n\*\*A:\*\* (.*?)(?=\n\n\*\*Q:|\Z)', re.DOTALL)
				qa_matches = qa_pattern.findall(content)
				for q, a in qa_matches:
					qa_list.append({'Question': q.strip(), 'Answer': a.strip().replace(" **","-").replace(":**",":").replace("*","").replace("\n\n",'\n').replace("**","")})

	#filtering data based on rules.				
	for i in range(len(qa_list)):
		if "{" in qa_list[i]['Question']:
			pattern1 = r"\{'title': '([^']*)'\s*,\s*'summary': '([^']*)'\}"
			pattern2 = r"\{'title': '([^']*)', 'summary': \"([^\"]*)\"\}"
			result1 = re.sub(pattern1, lambda match: match.group(1) , qa_list[i]["Question"])
			result2=re.sub(pattern2, lambda match: match.group(1) , qa_list[i]["Question"])
			if len(result1)>len(result2):
				qa_list[i]['Question']=result2
			else:
				qa_list[i]['Question']=result1

	for i in range(len(qa_list)):
		answers.append(qa_list[i]["Answer"])
		questions.append(qa_list[i]["Question"])
	filename = 'qa_pair_regulations.csv'

	#saving CSV files
	with open(filename, mode='w', newline='') as file:
		writer = csv.writer(file)
		writer.writerow(['Question', 'Answer'])
		for question, answer in zip(questions, answers):
			writer.writerow([question, answer])
	print(f"Data has been written to {filename}")






if __name__ == "__main__":

	#1. scarp all text from justice law website

	acts,regu=parse_xml_tree()
	array_to_json("data/laws.json",regu)

	array_to_json("data/acts.json",acts)


	# scrape_and_save()

	# #2. generate summary
	# print("running summary loop")
	# summary_func()
	# print("running QA loop")
	# #3. generate QA pairs
	# qa_func()
	

	# ###Summary generation is stochastic process sometimes it return empty files
	# #use the below function if necessary

	# #4. delete empty files
	# # remove_empty_text_files("data/text_summary/")


	#5. generating QA from single constiution file
	# mc=MultiChain()
	# with open("data/text_summary/01_constitution.txt", 'w') as f:
	# 	f.write(mc.summary().invoke({"text":read_text_files_from_folder("data/text_raw/01_constitution.txt")}).content)
	# with open("data/text_qa/01_constitution.txt", 'w') as f:
	# 	f.write(mc.qa().invoke({"summary":read_text_files_from_folder("data/text_summary/01_constitution.txt"),'title':" the Constitution Acts, 1867 to 1982"}).content)

    #6. parse and output qa to text		
	format_qa_to_csv()




