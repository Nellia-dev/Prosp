import { MigrationInterface, QueryRunner } from 'typeorm';

export class AddUserPlansAndQuotas1735679340000 implements MigrationInterface {
  name = 'AddUserPlansAndQuotas1735679340000';

  public async up(queryRunner: QueryRunner): Promise<void> {
    // Add plan and quota fields to users table
    await queryRunner.query(`
      ALTER TABLE "users" 
      ADD COLUMN "plan" character varying NOT NULL DEFAULT 'free',
      ADD COLUMN "currentLeadQuotaUsed" integer NOT NULL DEFAULT 0,
      ADD COLUMN "lastQuotaResetAt" timestamp,
      ADD COLUMN "prospectingJobId" character varying;
    `);

    // Create unique constraint for prospectingJobId
    await queryRunner.query(`
      ALTER TABLE "users" 
      ADD CONSTRAINT "UQ_users_prospectingJobId" UNIQUE ("prospectingJobId");
    `);

    // Add userId column to leads table
    await queryRunner.query(`
      ALTER TABLE "leads" 
      ADD COLUMN "userId" uuid;
    `);

    // Create foreign key constraint
    await queryRunner.query(`
      ALTER TABLE "leads" 
      ADD CONSTRAINT "FK_leads_userId" 
      FOREIGN KEY ("userId") REFERENCES "users"("id") 
      ON DELETE CASCADE ON UPDATE NO ACTION;
    `);

    // Create index for better performance
    await queryRunner.query(`
      CREATE INDEX "IDX_leads_userId" ON "leads" ("userId");
    `);

    // Initialize lastQuotaResetAt for existing users
    await queryRunner.query(`
      UPDATE "users" 
      SET "lastQuotaResetAt" = NOW() 
      WHERE "lastQuotaResetAt" IS NULL;
    `);
  }

  public async down(queryRunner: QueryRunner): Promise<void> {
    // Remove foreign key constraint and index
    await queryRunner.query(`DROP INDEX "IDX_leads_userId"`);
    await queryRunner.query(`ALTER TABLE "leads" DROP CONSTRAINT "FK_leads_userId"`);

    // Remove userId column from leads
    await queryRunner.query(`ALTER TABLE "leads" DROP COLUMN "userId"`);

    // Remove unique constraint from users
    await queryRunner.query(`ALTER TABLE "users" DROP CONSTRAINT "UQ_users_prospectingJobId"`);

    // Remove plan and quota columns from users
    await queryRunner.query(`
      ALTER TABLE "users" 
      DROP COLUMN "prospectingJobId",
      DROP COLUMN "lastQuotaResetAt",
      DROP COLUMN "currentLeadQuotaUsed",
      DROP COLUMN "plan";
    `);
  }
}
