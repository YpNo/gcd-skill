# Quickstart: Enable Shielded VM options

Source: https://documentation.s3ns.fr/compute/shielded-vm/docs/quickstart
Last updated: 2026-11-10

Some or all of the information on this page might not apply to Cloud de Confiance by S3NS. See [Differences from Google Cloud](/compute/shielded-vm/docs/tpc-differences) for more details.














- 





[

Home

](https://documentation.s3ns.fr/)






- 








[

Documentation

](https://documentation.s3ns.fr/docs)






- 








[

Compute

](https://documentation.s3ns.fr/docs/compute-area)






- 








[

Compute Engine

](https://documentation.s3ns.fr/compute/docs)






- 








[

Shielded VM

](https://documentation.s3ns.fr/compute/shielded-vm/docs)






- 








[

Guides

](https://documentation.s3ns.fr/compute/shielded-vm/docs/shielded-vm)


























# Quickstart: Enable Shielded VM options




Learn how to enable Shielded VM options by using the Cloud de Confiance console.





## Before you begin



Before you start this tutorial, complete the following steps:

- Create a VM instance with
[an OS that supports Shielded VM features](/compute/docs/images/os-details#security-features).
Learn more about
[creating a VM instance](/compute/docs/instances/create-start-instance).

- 

Verify that you have the following permissions on the VM.

- `compute.instances.updateShieldedInstanceConfig`

Learn more about
[managing access to Compute Engine resources](/compute/docs/access/managing-access-to-resources).






## Enable all Shielded VM options

- 

In the Cloud de Confiance console, go to the **VM instances** page.

[Go to **VM instances**](https://console.cloud.s3nscloud.fr/compute/instances) 

- 

Click the instance name to open the **VM instance details** page.

- 

Click stop **Stop**. If there is no **Stop** option, click
more_vert **More actions >** stop **Stop**.

- 

After the instance stops, click **Edit**.

- 

In the **Shielded VM** section, modify the Shielded VM options:

- Toggle **Turn on Secure Boot** to enable Secure Boot. Learn more about
[Secure Boot](/compute/shielded-vm/docs/shielded-vm#secure-boot).

- Toggle **Turn on vTPM** to enable the virtual trusted platform module
(vTPM). Learn more about [vTPM](/compute/shielded-vm/docs/shielded-vm#vtpm).

- Toggle **Turn on Integrity Monitoring** to enable integrity
monitoring. Learn more about
[integrity monitoring](/compute/shielded-vm/docs/shielded-vm#integrity-monitoring).

- 

Click **Save**.

- 

Click **Start** to start the instance.






## Clean up





To avoid incurring charges to your Cloud de Confiance account for
the resources used on this page, follow these steps.






- 

In the Cloud de Confiance console, go to the **VM instances** page.

[Go to **VM instances**](https://console.cloud.s3nscloud.fr/compute/instances) 

- 

In the row for the VM instance you created for this exercise, click **More
Actions**, and then select **Delete**.






## What's next



- Learn more about the [key concepts in Shielded VM](/compute/shielded-vm/docs/shielded-vm).

- Learn more about [modifying Shielded VM options](/compute/shielded-vm/docs/modifying-shielded-vm).