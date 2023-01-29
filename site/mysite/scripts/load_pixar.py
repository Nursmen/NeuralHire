from NeuralHire.models import Job
import csv


def run():
    with open('model\jobs.csv',encoding='utf8') as file:
        reader = csv.reader(file)
        next(reader)  # Advance past the header

        Job.objects.all().delete()

        for row in reader:
            print(row)
            if row[1] != '': 
                job = Job(title=row[0],
                            money=row[1],
                            knoladge=row[2],
                            addition = row[4],
                            city=row[5],
                            link=row[-1].replace('vacancy/search/?keywords=python/', ''))
                job.save()