import { MigrationInterface, QueryRunner } from "typeorm";

export class UserSeenLeadTable1750270675446 implements MigrationInterface {
    name = 'UserSeenLeadTable1750270675446'

    public async up(queryRunner: QueryRunner): Promise<void> {
        await queryRunner.query(`
            CREATE TABLE "user_seen_leads" (
                "userId" uuid NOT NULL,
                "leadId" uuid NOT NULL,
                "seenAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT "PK_user_seen_leads" PRIMARY KEY ("userId", "leadId"),
                CONSTRAINT "FK_user_seen_leads_userId" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE NO ACTION,
                CONSTRAINT "FK_user_seen_leads_leadId" FOREIGN KEY ("leadId") REFERENCES "leads"("id") ON DELETE CASCADE ON UPDATE NO ACTION
            )
        `);
    }

    public async down(queryRunner: QueryRunner): Promise<void> {
        await queryRunner.query(`
            DROP TABLE "user_seen_leads"
        `);
    }

}
