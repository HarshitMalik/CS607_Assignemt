import pandas as pd
import shutil
import os

def get_results(tm_output_dir, results_dir, text_output_dir, threshold = 0.35):
    doc_topics = pd.read_csv(tm_output_dir + 'doc-topics.csv')
    topic_terms = pd.read_csv(tm_output_dir + 'topic-terms.csv')

    total_topics = topic_terms ['topic'].max().item() + 1

    books = ['Gita', 'Quran', 'Taoist', 'Bible', 'GuruGranth']
    data = []

    for i in range(total_topics):
        df = doc_topics[doc_topics['topic'] == i]
        row = []
        count = 0
        for book in books:
            res = df[df['docname'].str.contains(book)].sort_values('proportion',ascending=False).head(5)
            pages = []
            for k in range(res.shape[0]):
                if res.iloc[k].proportion >= threshold:
                    pages.append(int(res.iloc[k].docname[:-4].split("_")[-1]))
            if len(pages) > 0:
                count += 1
            row.append(pages)
        row.append(topic_terms[topic_terms['topic']==i]['term'].values.tolist())
        if count > 1:
            data.append(row)

    output_df = pd.DataFrame(data, columns = books + ['analogous_terms'])

    if os.path.isdir(results_dir + 'similar_texts/'):
        shutil.rmtree(results_dir + 'similar_texts/')
    os.mkdir(results_dir + 'similar_texts/')

    output_df.to_csv(results_dir + 'results.csv')
    print('Final results saved at',results_dir + 'results.csv')

    for i in range(output_df.shape[0]):
        dir = results_dir + 'similar_texts/topic_'+str(i+1)+'/'
        os.mkdir(dir)
        for j in range(len(books)):
            pages = output_df.iloc[i,j]
            for page in pages:
                shutil.copyfile(text_output_dir+books[j]+'_page_'+str(page)+'.txt',dir+books[j]+'_page_'+str(page)+'.txt')
    print('Textual output saved at',results_dir + 'similar_texts/')
